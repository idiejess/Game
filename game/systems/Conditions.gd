class_name Conditions
extends RefCounted
## Evaluates a card `conditions` block against a GameState snapshot.
## Every check returns a reason string on failure so the dev panel can explain eligibility.


static func _in_range(value: int, rng: Dictionary) -> bool:
	if rng.has("min") and value < int(rng["min"]):
		return false
	if rng.has("max") and value > int(rng["max"]):
		return false
	return true


## Returns "" when satisfied, otherwise a short human-readable reason.
static func explain(cond: Dictionary, gs) -> String:
	if cond.is_empty():
		return ""
	for f in cond.get("flags_all", []):
		if not gs.has_flag(f):
			return "missing flag %s" % f
	var any_flags: Array = cond.get("flags_any", [])
	if not any_flags.is_empty():
		var ok := false
		for f in any_flags:
			if gs.has_flag(f):
				ok = true
				break
		if not ok:
			return "none of flags %s" % str(any_flags)
	for f in cond.get("flags_none", []):
		if gs.has_flag(f):
			return "blocked by flag %s" % f
	var res: Dictionary = cond.get("resources", {})
	for r in res:
		if not _in_range(gs.get_resource(r), res[r]):
			return "%s=%d not in %s" % [r, gs.get_resource(r), str(res[r])]
	var rel: Dictionary = cond.get("relationships", {})
	for c in rel:
		if not _in_range(gs.get_relationship(c), rel[c]):
			return "rel %s=%d not in %s" % [c, gs.get_relationship(c), str(rel[c])]
	var fac: Dictionary = cond.get("factions", {})
	for f in fac:
		if not _in_range(gs.get_faction(f), fac[f]):
			return "faction %s=%d not in %s" % [f, gs.get_faction(f), str(fac[f])]
	var ctr: Dictionary = cond.get("counters", {})
	for c in ctr:
		if not _in_range(gs.get_counter(c), ctr[c]):
			return "counter %s=%d not in %s" % [c, gs.get_counter(c), str(ctr[c])]
	if cond.has("run") and not _in_range(gs.run_number(), cond["run"]):
		return "run %d not in %s" % [gs.run_number(), str(cond["run"])]
	if cond.has("watch") and not _in_range(gs.watch, cond["watch"]):
		return "watch %d not in %s" % [gs.watch, str(cond["watch"])]
	for c in cond.get("seen_cards", []):
		if not gs.has_seen(c):
			return "requires seen %s" % c
	for c in cond.get("unseen_cards", []):
		if gs.has_seen(c):
			return "requires unseen %s" % c
	var seen_any: Array = cond.get("seen_cards_any", [])
	if not seen_any.is_empty():
		var ok2 := false
		for c in seen_any:
			if gs.has_seen(c):
				ok2 = true
				break
		if not ok2:
			return "requires any seen of %s" % str(seen_any)
	for u in cond.get("unlocks", []):
		if not gs.has_unlock(u):
			return "missing unlock %s" % u
	for u in cond.get("unlocks_none", []):
		if gs.has_unlock(u):
			return "blocked by unlock %s" % u
	var stages: Dictionary = cond.get("arc_stage", {})
	for a in stages:
		if not _in_range(gs.arc_stage(a), stages[a]):
			return "arc %s stage %d not in %s" % [a, gs.arc_stage(a), str(stages[a])]
	var statuses: Dictionary = cond.get("arc_status", {})
	for a in statuses:
		if gs.arc_status(a) != statuses[a]:
			return "arc %s status %s != %s" % [a, gs.arc_status(a), statuses[a]]
	for e in cond.get("endings_seen", []):
		if not gs.has_ending(e):
			return "requires ending %s" % e
	for e in cond.get("endings_unseen", []):
		if gs.has_ending(e):
			return "blocked by ending %s" % e
	return ""


static func satisfied(cond: Dictionary, gs) -> bool:
	return explain(cond, gs) == ""
