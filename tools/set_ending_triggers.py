#!/usr/bin/env python3
"""One-off content migration: give every ending a data-driven trigger (see docs/NARRATIVE_SYSTEM.md
"Ending triggers"). Idempotent; re-running rewrites the same triggers and order.

Trigger kinds (schemas/ending.schema.json):
  resource_edge + conditions : variant of a resource death, chosen when its conditions hold
                               (file order = priority; the plain end_res_* is the fallback)
  conditions [+ watch_min]   : checked after every watch, before the long-watch retirement
  long_watch + conditions    : candidates for the watch-100 retirement, first satisfied in file
                               order wins; end_ord_long_watch (watch_min only) is the fallback
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "content" / "endings" / "endings.json"

TRIGGERS = {
    # --- ordinary retirements at watch 100, in priority order
    "end_ord_jubilee": {"long_watch": True, "conditions": {"flags_all": ["jubilee_held"]}},
    "end_rev_tobin": {"long_watch": True, "conditions": {"flags_all": ["tobin_story_2"], "unlocks_none": ["unlock_cut_map"]}},
    "end_ord_quiet": {"long_watch": True, "conditions": {"relationships": {"ilse": {"min": 75}}, "resources": {"town": {"min": 60}}}},
    "end_ord_towns_keeper": {"long_watch": True, "conditions": {"resources": {"town": {"min": 75}}}},
    "end_ord_companys_keeper": {"long_watch": True, "conditions": {"resources": {"company": {"min": 75}}}},
    "end_ord_transferred": {"long_watch": True, "conditions": {"resources": {"company": {"min": 60}}, "counters": {"company_favors": {"min": 3}}}},
    "end_ord_long_watch": {"watch_min": 100},
    # --- false endings: conclusions that feel like solutions
    "end_false_killer": {"watch_min": 40, "conditions": {"flags_all": ["vosk_enemy", "hesse_has_story", "pressed_by_hesse"]}},
    "end_false_purchase": {"watch_min": 40, "conditions": {"flags_all": ["sorrel_purchase_offered"], "resources": {"company": {"max": 28}}}},
    "end_false_clearance": {"watch_min": 30, "conditions": {"flags_all": ["hullfolk_cleared"], "flags_none": ["allies_gathered"]}},
    "end_false_blessing": {"watch_min": 30, "conditions": {"flags_all": ["lamp_vigil_held", "wet_season"], "flags_none": ["knows_cut"]}},
    "end_false_hero": {"watch_min": 40, "conditions": {"flags_all": ["pressed_by_hesse", "praised_by_board"], "resources": {"company": {"min": 72}}}},
    # --- crisis endings: escalations that were not contained
    "end_crisis_fire": {"conditions": {"flags_all": ["fire_boatyard", "riot_brewing"], "resources": {"town": {"max": 22}}}},
    "end_crisis_riot": {"conditions": {"flags_all": ["riot_brewing"], "resources": {"town": {"max": 12}}}},
    "end_crisis_frost": {"conditions": {"flags_all": ["frost"], "resources": {"coffers": {"max": 25}, "traffic": {"max": 30}}}},
    "end_crisis_inquiry": {"conditions": {"flags_all": ["inquiry_pending"], "flags_any": ["compact_breached", "inspections_waived", "night_passages"]}},
    "end_crisis_fever": {"conditions": {"flags_all": ["fever_aboard"], "flags_none": ["quarantine"], "counters": {"fatigue": {"min": 12}}}},
    # --- revelations: resource-death variants that unlock a Ledger fact (priority = this order)
    "end_rev_sluice": {"resource_edge": {"resource": "water", "edge": "min"}, "conditions": {"flags_all": ["sluice_house_opened"]}},
    "end_rev_cipher": {"resource_edge": {"resource": "water", "edge": "min"}, "conditions": {"flags_all": ["cipher_solved"], "unlocks_none": ["unlock_cut_map"]}},
    "end_rev_letters": {"resource_edge": {"resource": "water", "edge": "max"}, "conditions": {"flags_all": ["undercroft_flooded"]}},
    "end_rev_file": {"resource_edge": {"resource": "company", "edge": "min"}, "conditions": {"flags_all": ["vosk_file_seen"]}},
    "end_rev_vosk": {"resource_edge": {"resource": "company", "edge": "min"}, "conditions": {"flags_all": ["vosk_ally"]}},
    "end_rev_survey": {"resource_edge": {"resource": "company", "edge": "min"}, "conditions": {"flags_all": ["read_survey"]}},
    "end_rev_crane": {"resource_edge": {"resource": "company", "edge": "min"}, "conditions": {"flags_all": ["crane_recruited"]}},
    "end_rev_song": {"resource_edge": {"resource": "town", "edge": "min"}, "conditions": {"flags_all": ["song_heard"]}},
    "end_rev_bram": {"resource_edge": {"resource": "town", "edge": "min"}, "conditions": {"flags_all": ["honored_remembered"]}},
}


def main():
    data = json.loads(PATH.read_text())
    by_id = {e["id"]: e for e in data["endings"]}
    for eid, trig in TRIGGERS.items():
        if eid not in by_id:
            raise SystemExit("unknown ending " + eid)
        by_id[eid]["trigger"] = trig
    order = {eid: i for i, eid in enumerate(TRIGGERS)}
    untouched = [e for e in data["endings"] if e["id"] not in order]
    touched = sorted((e for e in data["endings"] if e["id"] in order), key=lambda e: order[e["id"]])
    data["endings"] = untouched + touched
    PATH.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print("updated", len(TRIGGERS), "ending triggers")


if __name__ == "__main__":
    main()
