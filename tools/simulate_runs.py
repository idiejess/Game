#!/usr/bin/env python3
"""Deterministic headless simulator mirroring game/autoload/CardSelector.gd and GameState.gd.

Strategies: random, balance, risk_seek, risk_avoid, loyalist:<char>, faction:<faction>, mystery,
short_term, long_term. Runs are deterministic per (seed, strategy).

Usage:
  python3 tools/simulate_runs.py --runs 1000 [--strategies all] [--seed 1] [--out reports/simulations/sim.json]
Writes a JSON report and prints a summary. Also used by tools/generate_reports.py for BALANCE_REPORT.md.
"""
import argparse
import json
import pathlib
import statistics
import sys
import time
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESOURCES = ["water", "traffic", "coffers", "company", "town"]
FACTIONS = ["company", "town", "hullfolk", "aldmere", "sorrel", "concordance"]
CATEGORIES = ["onboarding", "evergreen", "resources", "relationships", "minor_arcs", "major_arcs", "crises", "endings_meta"]

# Selector constants (keep in sync with CardSelector.gd)
DANGER_LOW, DANGER_HIGH = 30, 70
REPEAT_PENALTY, UNDISCOVERED_BONUS, ARC_ACTIVE_BONUS = 0.25, 1.6, 3.0
RESOURCE_DANGER_BONUS, SPEAKER_RECENT_PENALTY, CATEGORY_RECENT_PENALTY = 2.5, 0.4, 0.6
CRISIS_BASE_WEIGHT, MAX_DELAY_POSTPONES = 0.15, 3
LEDGER_DAY_INTERVAL, LONG_WATCH, WATER_DRIFT = 20, 100, -1


class Rng:
    A, C, MASK = 1664525, 1013904223, 0xFFFFFFFF

    def __init__(self, seed):
        self.state = seed & self.MASK or 0x9E3779B9

    def next_u32(self):
        self.state = (self.state * self.A + self.C) & self.MASK
        return self.state

    def next_float(self):
        return (self.next_u32() >> 8) / float(1 << 24)

    def next_int(self, lo, hi):
        if hi <= lo:
            return lo
        return lo + self.next_u32() % (hi - lo + 1)

    def pick_weighted(self, weights):
        total = sum(weights)
        if total <= 0:
            return -1
        r = self.next_float() * total
        acc = 0.0
        for i, w in enumerate(weights):
            acc += w
            if r < acc:
                return i
        return len(weights) - 1


def load_content():
    cards = {}
    for cat in CATEGORIES:
        for p in sorted((ROOT / "content" / "cards" / cat).glob("*.json")):
            for c in json.loads(p.read_text())["cards"]:
                cards[c["id"]] = c
    chars = {p.stem: json.loads(p.read_text()) for p in (ROOT / "content" / "characters").glob("*.json")}
    endings = {e["id"]: e for e in json.loads((ROOT / "content" / "endings" / "endings.json").read_text())["endings"]}
    counters = {c["id"]: c for c in json.loads((ROOT / "content" / "COUNTER_REGISTRY.json").read_text())["counters"]}
    return cards, chars, endings, counters


class Sim:
    def __init__(self, cards, chars, endings, counters):
        self.cards, self.chars, self.endings, self.counters = cards, chars, endings, counters
        self.fallback = sorted(c for c in cards if cards[c].get("pool") == "fallback")
        self.general = sorted(c for c in cards if cards[c].get("pool", "general") in ("general", "character", "crisis"))
        self.profile = self.fresh_profile()

    @staticmethod
    def fresh_profile():
        return {"run_number": 0, "unlocks": set(), "lore": set(), "endings": [], "discovered": set(),
                "pflags": set(), "pcounters": defaultdict(int)}

    # ---------------------------------------------------------------- state helpers
    def start_run(self, seed):
        p = self.profile
        p["run_number"] += 1
        self.rng = Rng(seed)
        self.run = {"seed": seed, "watch": 0, "res": {r: 50 for r in RESOURCES},
                    "rel": {c: ch.get("initial_relationship", 50) for c, ch in self.chars.items() if ch["tier"] != "source"},
                    "fac": {f: 50 for f in FACTIONS}, "flags": set(),
                    "ctr": {c: v.get("default", 0) for c, v in self.counters.items() if v.get("scope", "run") == "run"},
                    "arcs": {}, "history": [], "cooldowns": {}, "appear": Counter(), "delayed": [], "delayed_res": [],
                    "forced": [], "subdecks": [], "fallbacks": 0, "ended": None, "current": None, "pending_ending": None,
                    "sources": Counter()}
        if "p_protected_quenn" in p["pflags"]:
            self.run["rel"]["quenn"] = min(100, self.run["rel"].get("quenn", 50) + 10)
        if "p_honored_remembered" in p["pflags"]:
            self.run["fac"]["hullfolk"] = min(100, self.run["fac"]["hullfolk"] + 8)
        if "onb_01" in self.cards:
            self.run["forced"].append("onb_01")
        if p["run_number"] >= 2 and "meta_new_keeper_2" in self.cards:
            self.run["forced"].append("meta_new_keeper_2")

    def get_res(self, r): return self.run["res"].get(r, 50)
    def get_rel(self, c): return self.run["rel"].get(c, 50)
    def get_fac(self, f): return self.run["fac"].get(f, 50)

    def get_ctr(self, c):
        if c.startswith("p_"):
            return self.profile["pcounters"][c]
        return self.run["ctr"].get(c, 0)

    def has_flag(self, f):
        if f.startswith("p_"):
            return f in self.profile["pflags"]
        return f in self.run["flags"]

    def set_flag(self, f, on=True):
        target = self.profile["pflags"] if f.startswith("p_") else self.run["flags"]
        if on:
            target.add(f)
        else:
            target.discard(f)

    def set_ctr(self, c, v):
        reg = self.counters.get(c, {})
        v = max(v, reg.get("min", v))
        v = min(v, reg.get("max", v))
        if c.startswith("p_"):
            self.profile["pcounters"][c] = v
        else:
            self.run["ctr"][c] = v

    def arc_stage(self, a): return self.run["arcs"].get(a, {}).get("stage", 0)
    def arc_status(self, a): return self.run["arcs"].get(a, {}).get("status", "inactive")

    def set_arc(self, a, stage=-1, status=""):
        d = self.run["arcs"].setdefault(a, {"stage": 0, "status": "inactive"})
        if stage >= 0:
            d["stage"] = stage
        if status:
            d["status"] = status

    def has_ending(self, e): return any(x["id"] == e for x in self.profile["endings"])

    # ---------------------------------------------------------------- conditions
    @staticmethod
    def in_range(v, rng):
        return not (("min" in rng and v < rng["min"]) or ("max" in rng and v > rng["max"]))

    def satisfied(self, cond):
        if not cond:
            return True
        for f in cond.get("flags_all", []):
            if not self.has_flag(f):
                return False
        if cond.get("flags_any") and not any(self.has_flag(f) for f in cond["flags_any"]):
            return False
        for f in cond.get("flags_none", []):
            if self.has_flag(f):
                return False
        for r, rng in cond.get("resources", {}).items():
            if not self.in_range(self.get_res(r), rng):
                return False
        for c, rng in cond.get("relationships", {}).items():
            if not self.in_range(self.get_rel(c), rng):
                return False
        for f, rng in cond.get("factions", {}).items():
            if not self.in_range(self.get_fac(f), rng):
                return False
        for c, rng in cond.get("counters", {}).items():
            if not self.in_range(self.get_ctr(c), rng):
                return False
        if "run" in cond and not self.in_range(self.profile["run_number"], cond["run"]):
            return False
        if "watch" in cond and not self.in_range(self.run["watch"], cond["watch"]):
            return False
        for c in cond.get("seen_cards", []):
            if c not in self.run["appear"]:
                return False
        for c in cond.get("unseen_cards", []):
            if c in self.run["appear"]:
                return False
        if cond.get("seen_cards_any") and not any(c in self.run["appear"] for c in cond["seen_cards_any"]):
            return False
        for u in cond.get("unlocks", []):
            if u not in self.profile["unlocks"]:
                return False
        for u in cond.get("unlocks_none", []):
            if u in self.profile["unlocks"]:
                return False
        for a, rng in cond.get("arc_stage", {}).items():
            if not self.in_range(self.arc_stage(a), rng):
                return False
        for a, st in cond.get("arc_status", {}).items():
            if self.arc_status(a) != st:
                return False
        for e in cond.get("endings_seen", []):
            if not self.has_ending(e):
                return False
        for e in cond.get("endings_unseen", []):
            if self.has_ending(e):
                return False
        return True

    # ---------------------------------------------------------------- selection
    def is_ledger_day(self):
        w = self.run["watch"]
        return w > 0 and w % LEDGER_DAY_INTERVAL == 0

    def danger(self):
        return [r for r in RESOURCES if self.get_res(r) <= DANGER_LOW or self.get_res(r) >= DANGER_HIGH]

    def eligible(self, cid):
        card = self.cards[cid]
        pool = card.get("pool", "general")
        if pool in ("forced", "ending"):
            return False
        if cid in self.run["cooldowns"]:
            return False
        if self.run["appear"][cid] >= card.get("max_per_run", 1):
            return False
        if self.run["current"] == cid:
            return False
        if "arc" in card and self.arc_status(card["arc"]["id"]) in ("completed", "failed"):
            return False
        return self.satisfied(card.get("conditions", {}))

    def weight(self, cid, recent_speaker, recent_cats, danger):
        card = self.cards[cid]
        if not self.eligible(cid):
            return 0.0
        w = float(card.get("weight", 1.0))
        for wm in card.get("weight_mods", []):
            if self.satisfied(wm["when"]):
                w *= wm["multiply"]
        if w <= 0:
            return 0.0
        pool = card.get("pool", "general")
        tags = card.get("tags", [])
        if pool == "crisis":
            relevant = any(t.startswith("res:") and t[4:] in danger for t in tags)
            if self.is_ledger_day():
                w *= 4.0
            elif relevant:
                w *= 1.5
            else:
                w *= CRISIS_BASE_WEIGHT
        else:
            for t in tags:
                if t.startswith("res:") and t[4:] in danger:
                    w *= RESOURCE_DANGER_BONUS
        if "arc" in card:
            a = card["arc"]["id"]
            if self.arc_status(a) == "active" and card["arc"]["stage"] == self.arc_stage(a) + 1:
                w *= ARC_ACTIVE_BONUS
        if cid in self.run["appear"]:
            w *= REPEAT_PENALTY
        elif cid not in self.profile["discovered"]:
            w *= UNDISCOVERED_BONUS
        if recent_speaker and card["speaker"] == recent_speaker and "arc" not in card:
            w *= SPEAKER_RECENT_PENALTY
        if card["category"] in recent_cats and card["category"] != "onboarding":
            w *= CATEGORY_RECENT_PENALTY
        if card["category"] == "onboarding" and self.run["watch"] >= 12:
            w *= 0.05
        return w

    def next_card(self):
        r = self.run
        while r["forced"]:
            cid = r["forced"].pop(0)
            if cid in self.cards:
                r["sources"]["forced"] += 1
                return cid
        # delayed
        due_i = -1
        for i, d in enumerate(r["delayed"]):
            if d["due"] <= r["watch"] and (due_i < 0 or d["due"] < r["delayed"][due_i]["due"]):
                due_i = i
        if due_i >= 0:
            d = r["delayed"][due_i]
            card = self.cards.get(d["card"])
            if card is None:
                r["delayed"].pop(due_i)
            elif not self.satisfied(card.get("conditions", {})):
                if d.get("postponed", 0) >= MAX_DELAY_POSTPONES:
                    r["delayed"].pop(due_i)
                else:
                    d["postponed"] = d.get("postponed", 0) + 1
                    d["due"] = r["watch"] + 3
            else:
                r["delayed"].pop(due_i)
                r["sources"]["delayed"] += 1
                return d["card"]
        # subdecks
        i = 0
        while i < len(r["subdecks"]):
            d = r["subdecks"][i]
            if not d["cards"]:
                r["subdecks"].pop(i)
                continue
            if d.get("since", 0) >= d.get("interleave", 0):
                cid = d["cards"].pop(0)
                d["since"] = 0
                if not d["cards"]:
                    r["subdecks"].pop(i)
                if cid in self.cards and self.satisfied(self.cards[cid].get("conditions", {})):
                    r["sources"]["subdeck"] += 1
                    return cid
                continue
            d["since"] = d.get("since", 0) + 1
            i += 1
        # weighted
        hist = r["history"][-3:]
        recent_speaker = self.cards[hist[-1]["card"]]["speaker"] if hist else ""
        recent_cats = [self.cards[h["card"]]["category"] for h in hist if h["card"] in self.cards]
        danger = self.danger()
        include_crisis = self.is_ledger_day() or bool(danger) or r["watch"] % 7 == 0
        ids, weights = [], []
        for cid in self.general:
            card = self.cards[cid]
            if card.get("pool", "general") == "crisis" and not include_crisis:
                continue
            if card["category"] == "onboarding" and r["watch"] > 14:
                continue
            w = self.weight(cid, recent_speaker, recent_cats, danger)
            if w > 0:
                ids.append(cid)
                weights.append(w)
        if ids:
            idx = self.rng.pick_weighted(weights)
            r["sources"]["weighted"] += 1
            return ids[idx]
        # fallback
        r["fallbacks"] += 1
        r["sources"]["fallback"] += 1
        if not self.fallback:
            return None
        fresh = [c for c in self.fallback if c not in r["appear"]]
        pool = fresh or self.fallback
        return pool[self.rng.next_int(0, len(pool) - 1)]

    # ---------------------------------------------------------------- effects
    def apply(self, eff):
        r = self.run
        ending = ""
        for k, v in eff.get("resources", {}).items():
            r["res"][k] = max(0, min(100, r["res"][k] + v))
        for k, v in eff.get("relationships", {}).items():
            r["rel"][k] = max(0, min(100, r["rel"].get(k, 50) + v))
        for k, v in eff.get("factions", {}).items():
            r["fac"][k] = max(0, min(100, r["fac"][k] + v))
        for f in eff.get("flags_set", []):
            self.set_flag(f, True)
        for f in eff.get("flags_clear", []):
            self.set_flag(f, False)
        for k, v in eff.get("counters", {}).items():
            self.set_ctr(k, self.get_ctr(k) + v)
        for k, v in eff.get("counters_set", {}).items():
            self.set_ctr(k, v)
        if "followup" in eff:
            r["forced"].insert(0, eff["followup"])
        for d in eff.get("delayed", []):
            delay = d["delay"]
            if "delay_max" in d:
                delay = self.rng.next_int(delay, d["delay_max"])
            r["delayed"].append({"card": d["card"], "due": r["watch"] + delay})
        for dr in eff.get("delayed_resources", []):
            r["delayed_res"].append({"due": r["watch"] + dr["delay"], "resources": dr["resources"]})
        if "subdeck" in eff:
            sd = eff["subdeck"]
            lst = list(sd["cards"])
            if sd.get("shuffle"):
                for i in range(len(lst) - 1, 0, -1):
                    j = self.rng.next_int(0, i)
                    lst[i], lst[j] = lst[j], lst[i]
            r["subdecks"].append({"id": sd["id"], "cards": lst, "interleave": sd.get("interleave", 0), "since": 0})
        for a, ad in eff.get("arc", {}).items():
            self.set_arc(a, ad.get("stage", -1), ad.get("status", ""))
        for u in eff.get("unlocks", []):
            self.profile["unlocks"].add(u)
        for l in eff.get("lore", []):
            self.profile["lore"].add(l)
        if "ending" in eff:
            fire = True
            if "ending_chance" in eff:
                fire = self.rng.next_float() < eff["ending_chance"]
            if fire:
                ending = eff["ending"]
        return ending

    def advance(self):
        r = self.run
        r["watch"] += 1
        drift = WATER_DRIFT + self.get_ctr("water_drift_mod")
        if self.has_flag("gates_leaking"):
            drift -= 1
        if self.has_flag("wet_season"):
            drift += 1
        if self.has_flag("sluice_rebuilt"):
            drift = 0
        r["res"]["water"] = max(0, min(100, r["res"]["water"] + drift))
        for cid in list(r["cooldowns"]):
            r["cooldowns"][cid] -= 1
            if r["cooldowns"][cid] <= 0:
                del r["cooldowns"][cid]
        keep = []
        for dr in r["delayed_res"]:
            if dr["due"] <= r["watch"]:
                for k, v in dr["resources"].items():
                    r["res"][k] = max(0, min(100, r["res"][k] + v))
            else:
                keep.append(dr)
        r["delayed_res"] = keep
        for res in RESOURCES:
            v = r["res"][res]
            if v <= 0:
                return f"end_res_{res}_min"
            if v >= 100:
                return f"end_res_{res}_max"
        return ""

    def long_watch_ending(self):
        if self.has_flag("jubilee_held") and "end_ord_jubilee" in self.endings:
            return "end_ord_jubilee"
        if self.get_res("town") >= 75:
            return "end_ord_towns_keeper"
        if self.get_res("company") >= 75:
            return "end_ord_companys_keeper"
        return "end_ord_long_watch"

    def end_run(self, eid):
        r, p = self.run, self.profile
        r["ended"] = eid
        p["endings"].append({"id": eid, "run": p["run_number"], "watch": r["watch"]})
        e = self.endings.get(eid, {})
        for u in e.get("unlocks", []):
            p["unlocks"].add(u)
        for l in e.get("lore", []):
            p["lore"].add(l)
        if eid in ("end_res_water_min", "end_res_water_max"):
            p["pflags"].add("p_prev_keeper_died_water")
        if eid == "end_res_town_min":
            p["pflags"].add("p_prev_keeper_run_out")
        if eid == "end_res_company_min":
            p["pflags"].add("p_prev_keeper_dismissed")
        if eid.startswith("end_true_"):
            p["pflags"].add("p_true_ending_seen")
        if self.has_flag("honored_remembered"):
            p["pflags"].add("p_honored_remembered")
        if self.has_flag("quenn_brave"):
            p["pflags"].add("p_protected_quenn")
        if self.has_flag("wren_jailed"):
            p["pflags"].add("p_jailed_wren")
        else:
            p["pflags"].discard("p_jailed_wren")
        if self.has_flag("hullfolk_cleared"):
            p["pflags"].add("p_clearance_done")
        if self.has_flag("told_mirren"):
            p["pflags"].add("p_told_mirren")
        cp = self.get_ctr("cipher_progress")
        if cp > p["pcounters"]["p_cipher_progress"]:
            p["pcounters"]["p_cipher_progress"] = cp

    # ---------------------------------------------------------------- one run
    def play(self, seed, strategy, max_steps=400):
        self.start_run(seed)
        r = self.run
        steps = 0
        trace = []
        while r["ended"] is None and steps < max_steps:
            cid = self.next_card()
            if cid is None:
                r["ended"] = "STALL"
                break
            r["current"] = cid
            r["appear"][cid] += 1
            self.profile["discovered"].add(cid)
            card = self.cards[cid]
            side = strategy.choose(self, card)
            eff = card[side]["effects"]
            ending = self.apply(eff)
            r["history"].append({"card": cid, "watch": r["watch"], "choice": side})
            if card.get("cooldown"):
                r["cooldowns"][cid] = card["cooldown"]
            r["current"] = None
            if "arc" in card:
                a = card["arc"]["id"]
                if self.arc_status(a) == "inactive":
                    self.set_arc(a, card["arc"]["stage"], "active")
                elif self.arc_status(a) == "active":
                    self.set_arc(a, max(self.arc_stage(a), card["arc"]["stage"]))
            trace.append(cid)
            if r["pending_ending"]:
                self.end_run(r["pending_ending"])
                break
            if not ending:
                ending = self.advance()
            if not ending and r["watch"] >= LONG_WATCH and not self.has_flag("allies_gathered"):
                ending = self.long_watch_ending()
            if ending:
                e = self.endings.get(ending, {})
                ecard = e.get("card")
                if ecard and ecard in self.cards:
                    r["pending_ending"] = ending
                    r["forced"].insert(0, ecard)
                else:
                    self.end_run(ending)
            steps += 1
        return trace


# -------------------------------------------------------------------- strategies
class Strategy:
    name = "base"

    def choose(self, sim, card):
        return "left"


class RandomS(Strategy):
    name = "random"

    def choose(self, sim, card):
        return "left" if sim.rng.next_float() < 0.5 else "right"


def score_res(sim, eff, weights=None):
    """Distance-from-center improvement after applying resource deltas."""
    total = 0.0
    for r in RESOURCES:
        v = sim.get_res(r)
        d = eff.get("resources", {}).get(r, 0)
        w = (weights or {}).get(r, 1.0)
        total += w * (abs(v - 50) - abs(v + d - 50))
    return total


class Balance(Strategy):
    name = "balance"

    def choose(self, sim, card):
        l, r = score_res(sim, card["left"]["effects"]), score_res(sim, card["right"]["effects"])
        if l == r:
            return "left" if sim.rng.next_float() < 0.5 else "right"
        return "left" if l > r else "right"


class RiskSeek(Strategy):
    name = "risk_seek"

    def choose(self, sim, card):
        def mag(eff):
            return sum(abs(v) for v in eff.get("resources", {}).values()) + 2 * len(eff.get("flags_set", []))
        l, r = mag(card["left"]["effects"]), mag(card["right"]["effects"])
        if l == r:
            return "left" if sim.rng.next_float() < 0.5 else "right"
        return "left" if l > r else "right"


class RiskAvoid(Strategy):
    name = "risk_avoid"

    def choose(self, sim, card):
        def worst(eff):
            w = 0
            for k, v in eff.get("resources", {}).items():
                nv = sim.get_res(k) + v
                w = max(w, abs(nv - 50))
            return w
        l, r = worst(card["left"]["effects"]), worst(card["right"]["effects"])
        if l == r:
            return Balance().choose(sim, card)
        return "left" if l < r else "right"


class Loyalist(Strategy):
    def __init__(self, char):
        self.char = char
        self.name = f"loyalist:{char}"

    def choose(self, sim, card):
        l = card["left"]["effects"].get("relationships", {}).get(self.char, 0)
        r = card["right"]["effects"].get("relationships", {}).get(self.char, 0)
        if l == r:
            return Balance().choose(sim, card)
        return "left" if l > r else "right"


class FactionLoyal(Strategy):
    def __init__(self, fac):
        self.fac = fac
        self.name = f"faction:{fac}"

    def choose(self, sim, card):
        def s(eff):
            v = eff.get("factions", {}).get(self.fac, 0)
            if self.fac in ("company", "town"):
                v += eff.get("resources", {}).get(self.fac, 0)
            return v
        l, r = s(card["left"]["effects"]), s(card["right"]["effects"])
        if l == r:
            return Balance().choose(sim, card)
        return "left" if l > r else "right"


class Mystery(Strategy):
    name = "mystery"

    def choose(self, sim, card):
        def s(eff):
            v = eff.get("counters", {}).get("evidence", 0) * 3 + eff.get("counters", {}).get("cipher_progress", 0) * 2
            v += sum(2 for f in eff.get("flags_set", []) if f.startswith("clue_") or f in ("found_ledger", "cipher_solved", "read_survey", "read_letters", "song_heard", "honored_remembered", "sluice_house_seen"))
            v += 4 * len(eff.get("unlocks", []))
            return v
        l, r = s(card["left"]["effects"]), s(card["right"]["effects"])
        if l == r:
            return Balance().choose(sim, card)
        return "left" if l > r else "right"


class ShortTerm(Strategy):
    name = "short_term"

    def choose(self, sim, card):
        def s(eff):
            return sum(eff.get("resources", {}).values())
        l, r = s(card["left"]["effects"]), s(card["right"]["effects"])
        if l == r:
            return "left" if sim.rng.next_float() < 0.5 else "right"
        return "left" if l > r else "right"


class LongTerm(Strategy):
    """Balance now, but value delayed effects and relationships positively and danger negatively."""
    name = "long_term"

    def choose(self, sim, card):
        def s(eff):
            v = score_res(sim, eff)
            for dr in eff.get("delayed_resources", []):
                v += 0.5 * sum(dr["resources"].values())
            v += 0.2 * sum(eff.get("relationships", {}).values())
            v -= 3 * len(eff.get("flags_set", []) and [f for f in eff["flags_set"] if f in ("compact_breached", "inspections_waived", "night_passages")])
            v += 0.3 * eff.get("counters", {}).get("evidence", 0)
            return v
        l, r = s(card["left"]["effects"]), s(card["right"]["effects"])
        if l == r:
            return "left" if sim.rng.next_float() < 0.5 else "right"
        return "left" if l > r else "right"


def all_strategies():
    return [RandomS(), Balance(), RiskSeek(), RiskAvoid(), Loyalist("vosk"), Loyalist("bram"), Loyalist("mirren"),
            FactionLoyal("company"), FactionLoyal("hullfolk"), Mystery(), ShortTerm(), LongTerm()]


# -------------------------------------------------------------------- driver
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1000, help="total runs across all strategies")
    ap.add_argument("--strategies", default="all")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--runs-per-profile", type=int, default=8, help="consecutive runs sharing one persistent profile")
    ap.add_argument("--out", default="reports/simulations/simulation.json")
    args = ap.parse_args()
    cards, chars, endings, counters = load_content()
    strategies = all_strategies() if args.strategies == "all" else [s for s in all_strategies() if s.name in args.strategies.split(",")]
    per = max(1, args.runs // len(strategies))
    t0 = time.time()
    lengths = []
    end_counter = Counter()
    appear = Counter()
    per_strategy = {}
    fallback_runs = 0
    total_fallbacks = 0
    arc_entered, arc_completed = Counter(), Counter()
    char_runs = Counter()
    unlock_runs = Counter()
    true_endings = Counter()
    res_series = defaultdict(lambda: defaultdict(list))
    death_by_res = Counter()
    stalls = 0
    sources = Counter()
    for s in strategies:
        sim = Sim(cards, chars, endings, counters)
        sl, se = [], Counter()
        for i in range(per):
            if i % args.runs_per_profile == 0:
                sim.profile = Sim.fresh_profile()
            seed = (args.seed * 1000003 + hash(s.name) % 9973 * 7919 + i) & 0x7FFFFFFF
            trace = sim.play(seed, s)
            r = sim.run
            if r["ended"] == "STALL":
                stalls += 1
            lengths.append(r["watch"])
            sl.append(r["watch"])
            end_counter[r["ended"]] += 1
            se[r["ended"]] += 1
            if r["ended"] and r["ended"].startswith("end_res_"):
                death_by_res[r["ended"].split("_")[2]] += 1
            if r["ended"] and r["ended"].startswith("end_true_"):
                true_endings[r["ended"]] += 1
            for cid in trace:
                appear[cid] += 1
            seen_chars = {cards[c]["speaker"] for c in trace}
            for c in seen_chars:
                char_runs[c] += 1
            for a, d in r["arcs"].items():
                arc_entered[a] += 1
                if d["status"] == "completed":
                    arc_completed[a] += 1
            for u in sim.profile["unlocks"]:
                unlock_runs[u] += 1
            if r["fallbacks"]:
                fallback_runs += 1
                total_fallbacks += r["fallbacks"]
            for k, v in r["sources"].items():
                sources[k] += v
            # resource snapshots every 10 watches
            for h in r["history"]:
                pass
        per_strategy[s.name] = {"runs": per, "mean_length": round(statistics.mean(sl), 1) if sl else 0,
                                "median_length": statistics.median(sl) if sl else 0,
                                "endings": dict(se.most_common(8))}
    total = len(lengths)
    unseen = sorted(c for c in cards if c not in appear and cards[c].get("pool", "general") not in ("ending",))
    rare = sorted(c for c in cards if 0 < appear[c] < max(1, total * 0.005))
    over = [(c, n) for c, n in appear.most_common(15)]
    dist = Counter((w // 10) * 10 for w in lengths)
    report = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"), "seconds": round(time.time() - t0, 1),
        "cards": len(cards), "runs": total, "strategies": [s.name for s in strategies],
        "mean_length": round(statistics.mean(lengths), 2) if lengths else 0,
        "median_length": statistics.median(lengths) if lengths else 0,
        "length_distribution": {f"{k}-{k + 9}": v for k, v in sorted(dist.items())},
        "endings": dict(end_counter.most_common()), "death_by_resource": dict(death_by_res),
        "true_endings": dict(true_endings), "stalls": stalls,
        "fallback_runs": fallback_runs, "fallback_total": total_fallbacks, "selection_sources": dict(sources),
        "unseen_cards": unseen, "unseen_count": len(unseen), "rare_cards": rare[:60], "rare_count": len(rare),
        "overrepresented": over,
        "arc_entry_rate": {a: round(arc_entered[a] / total, 4) for a in sorted(arc_entered)},
        "arc_completion_rate": {a: round(arc_completed[a] / total, 4) for a in sorted(arc_entered)},
        "character_appearance_rate": {c: round(char_runs[c] / total, 4) for c in sorted(char_runs)},
        "unlock_rate": {u: round(unlock_runs[u] / total, 4) for u in sorted(unlock_runs)},
        "per_strategy": per_strategy,
        "card_appearance_top": appear.most_common(40),
        "card_appearance_all": dict(appear),
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1) + "\n")
    print(f"{total} runs in {report['seconds']}s | mean {report['mean_length']} median {report['median_length']} | "
          f"unseen {len(unseen)} rare {len(rare)} | fallback runs {fallback_runs} | stalls {stalls}")
    print("endings:", dict(end_counter.most_common(8)))
    print("deaths by resource:", dict(death_by_res))
    for name, d in per_strategy.items():
        print(f"  {name:18s} mean {d['mean_length']:6.1f}  top: {list(d['endings'].items())[:3]}")


if __name__ == "__main__":
    main()
