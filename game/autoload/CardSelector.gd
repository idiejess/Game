extends Node
## State-aware weighted card selection. Deterministic given the run seed.
##
## Order of operations (see docs/NARRATIVE_SYSTEM.md):
##  1. forced queue  2. due delayed cards  3. active sub-decks  4. Ledger Day crisis check
##  5. weighted general/character/crisis pools with eligibility filtering, cooldowns,
##     repetition protection, arc priority and dynamic resource weights  6. fallback.

signal fallback_used(unexpected: bool)

const DANGER_LOW := 30
const DANGER_HIGH := 70
const REPEAT_PENALTY := 0.25        # weight multiplier for cards already seen this run
const UNDISCOVERED_BONUS := 1.6     # cards never seen in any run
const ARC_ACTIVE_BONUS := 3.0       # next-stage cards of active arcs
const RESOURCE_DANGER_BONUS := 2.5  # cards tagged res:<x> when x is in a danger band
const SPEAKER_RECENT_PENALTY := 0.4 # same speaker as the previous card
const CATEGORY_RECENT_PENALTY := 0.6
const CRISIS_BASE_WEIGHT := 0.15    # crisis-pool cards outside Ledger Day / danger
const MAX_DELAY_POSTPONES := 3

var last_selection_debug: Dictionary = {}


## Returns the next card id, or "" if the run has ended.
func next_card() -> String:
	var gs = GameState
	if not gs.in_run():
		return ""
	last_selection_debug = {"source": "", "candidates": 0}

	# 1. forced
	var fq: Array = gs.run["forced_queue"]
	while not fq.is_empty():
		var cid: String = fq.pop_front()
		if ContentDB.has_card(cid):
			last_selection_debug["source"] = "forced"
			return cid

	# 2. delayed
	var due := _pop_due_delayed()
	if due != "":
		last_selection_debug["source"] = "delayed"
		return due

	# 3. sub-decks
	var sd := _next_subdeck_card()
	if sd != "":
		last_selection_debug["source"] = "subdeck"
		return sd

	# 4/5. weighted
	var picked := _pick_weighted()
	if picked != "":
		return picked

	# 6. fallback
	var fb := _pick_fallback()
	var unexpected := ContentDB.cards.size() > 50
	gs.run["fallback_count"] = int(gs.run.get("fallback_count", 0)) + 1
	gs.last_fallback_unexpected = unexpected
	last_selection_debug["source"] = "fallback"
	fallback_used.emit(unexpected)
	if unexpected:
		push_warning("[CardSelector] fallback card used unexpectedly at watch %d" % gs.watch)
	return fb


func _pop_due_delayed() -> String:
	var gs = GameState
	var list: Array = gs.run["delayed"]
	if list.is_empty():
		return ""
	# earliest due first; stable by insertion order
	var best_i := -1
	for i in range(list.size()):
		if int(list[i]["due"]) <= gs.watch:
			if best_i < 0 or int(list[i]["due"]) < int(list[best_i]["due"]):
				best_i = i
	if best_i < 0:
		return ""
	var entry: Dictionary = list[best_i]
	var cid: String = entry["card"]
	var card := ContentDB.get_card(cid)
	if card.is_empty():
		list.remove_at(best_i)
		return ""
	var reason := Conditions.explain(card.get("conditions", {}), gs)
	if reason != "":
		var n := int(entry.get("postponed", 0))
		if n >= MAX_DELAY_POSTPONES:
			list.remove_at(best_i)
			push_warning("[CardSelector] dropped delayed card %s: %s" % [cid, reason])
			return ""
		entry["postponed"] = n + 1
		entry["due"] = gs.watch + 3
		return ""
	list.remove_at(best_i)
	return cid


func _next_subdeck_card() -> String:
	var gs = GameState
	var decks: Array = gs.run["subdecks"]
	var i := 0
	while i < decks.size():
		var d: Dictionary = decks[i]
		if d["cards"].is_empty():
			decks.remove_at(i)
			continue
		var since := int(d.get("since", 0))
		if since >= int(d.get("interleave", 0)):
			var cid: String = d["cards"].pop_front()
			d["since"] = 0
			if d["cards"].is_empty():
				decks.remove_at(i)
			if ContentDB.has_card(cid):
				var reason := Conditions.explain(ContentDB.get_card(cid).get("conditions", {}), gs)
				if reason == "":
					return cid
			continue
		d["since"] = since + 1
		i += 1
	return ""


func _is_ledger_day() -> bool:
	var w: int = GameState.watch
	return w > 0 and w % GameState.LEDGER_DAY_INTERVAL == 0


func _danger_resources() -> Array:
	var out: Array = []
	for r in GameState.RESOURCES:
		var v: int = GameState.get_resource(r)
		if v <= DANGER_LOW or v >= DANGER_HIGH:
			out.append(r)
	return out


## Base eligibility shared by every pool. Returns "" or a reason.
func eligibility_reason(cid: String) -> String:
	var gs = GameState
	var card := ContentDB.get_card(cid)
	if card.is_empty():
		return "unknown card"
	var pool: String = card.get("pool", "general")
	if pool == "forced":
		return "forced-only card"
	if pool == "ending":
		return "ending-only card"
	if gs.run["cooldowns"].has(cid):
		return "cooldown %d" % int(gs.run["cooldowns"][cid])
	var seen := int(gs.run["appearances"].get(cid, 0))
	if seen >= int(card.get("max_per_run", 1)):
		return "exhausted (%d/%d)" % [seen, int(card.get("max_per_run", 1))]
	if gs.run.get("current_card", null) == cid:
		return "currently shown"
	if card.has("arc"):
		var a: String = card["arc"]["id"]
		var st := gs.arc_status(a)
		if st == "completed" or st == "failed":
			return "arc %s is %s" % [a, st]
	return Conditions.explain(card.get("conditions", {}), gs)


## Full weight for a card given current state; 0 if ineligible.
func weight_for(cid: String, recent_speaker: String = "", recent_categories: Array = []) -> float:
	var gs = GameState
	if eligibility_reason(cid) != "":
		return 0.0
	var card := ContentDB.get_card(cid)
	var w := float(card.get("weight", 1.0))
	for wm in card.get("weight_mods", []):
		if Conditions.satisfied(wm["when"], gs):
			w *= float(wm["multiply"])
	if w <= 0.0:
		return 0.0
	var pool: String = card.get("pool", "general")
	var danger := _danger_resources()
	if pool == "crisis":
		var relevant := false
		for t in card.get("tags", []):
			if t.begins_with("res:") and danger.has(t.substr(4)):
				relevant = true
		if _is_ledger_day():
			w *= 4.0
		elif relevant:
			w *= 1.5
		else:
			w *= CRISIS_BASE_WEIGHT
	else:
		for t in card.get("tags", []):
			if t.begins_with("res:") and danger.has(t.substr(4)):
				w *= RESOURCE_DANGER_BONUS
	if card.has("arc"):
		var a: String = card["arc"]["id"]
		if gs.arc_status(a) == "active" and int(card["arc"]["stage"]) == gs.arc_stage(a) + 1:
			w *= ARC_ACTIVE_BONUS
	if gs.run["appearances"].has(cid):
		w *= REPEAT_PENALTY
	elif not gs.profile["discovered_cards"].has(cid):
		w *= UNDISCOVERED_BONUS
	if recent_speaker != "" and card["speaker"] == recent_speaker and not card.has("arc"):
		w *= SPEAKER_RECENT_PENALTY
	if recent_categories.has(card["category"]) and card["category"] != "onboarding":
		w *= CATEGORY_RECENT_PENALTY
	if card["category"] == "onboarding" and gs.watch >= 12:
		w *= 0.05
	return w


func _candidate_ids() -> Array:
	# Indexes reduce the pool: onboarding only early, crisis pool only when relevant, arcs only when not closed.
	var gs = GameState
	var ids: Array = []
	var danger := _danger_resources()
	var include_crisis: bool = _is_ledger_day() or not danger.is_empty() or gs.watch % 7 == 0
	for cid in ContentDB.unconditional_general + ContentDB.conditional_general:
		var card: Dictionary = ContentDB.cards[cid]
		var pool: String = card.get("pool", "general")
		if pool == "crisis" and not include_crisis:
			continue
		if card["category"] == "onboarding" and gs.watch > 14:
			continue
		ids.append(cid)
	return ids


func _pick_weighted() -> String:
	var gs = GameState
	var hist: Array = gs.recent_history(3)
	var recent_speaker := ""
	var recent_categories: Array = []
	if not hist.is_empty():
		var last := ContentDB.get_card(hist[hist.size() - 1]["card"])
		recent_speaker = str(last.get("speaker", ""))
	for h in hist:
		var c := ContentDB.get_card(h["card"])
		if not c.is_empty():
			recent_categories.append(c["category"])
	var ids := _candidate_ids()
	var eligible: Array = []
	var weights: Array = []
	for cid in ids:
		var w := weight_for(cid, recent_speaker, recent_categories)
		if w > 0.0:
			eligible.append(cid)
			weights.append(w)
	last_selection_debug["candidates"] = eligible.size()
	if eligible.is_empty():
		return ""
	var idx: int = gs.rng.pick_weighted(weights)
	gs.run["rng_state"] = gs.rng.state
	last_selection_debug["source"] = "weighted"
	last_selection_debug["picked_weight"] = weights[idx]
	return eligible[idx]


func _pick_fallback() -> String:
	var gs = GameState
	var fbs: Array = ContentDB.fallback_cards
	if fbs.is_empty():
		return ""
	# Prefer fallback cards not yet used this run.
	var fresh: Array = []
	for cid in fbs:
		if not gs.run["appearances"].has(cid):
			fresh.append(cid)
	var pool: Array = fresh if not fresh.is_empty() else fbs
	return pool[gs.rng.next_int(0, pool.size() - 1)]


## Debug listing: [{id, weight, reason}] for the dev panel.
func explain_all(limit: int = 40) -> Array:
	var out: Array = []
	for cid in ContentDB.cards.keys():
		var reason := eligibility_reason(cid)
		var w := 0.0
		if reason == "":
			w = weight_for(cid)
		out.append({"id": cid, "weight": w, "reason": reason})
	out.sort_custom(func(a, b): return a["weight"] > b["weight"])
	return out.slice(0, limit)
