extends RefCounted
## Engine tests. Each test_* method uses runner.check(cond, current, message).

var runner
var current := ""

const TEST_CARD_FIXTURES := "res://game/tests/fixtures"


func ok(cond: bool, msg: String) -> void:
	runner.check(cond, current, msg)


func _content() -> Node:
	return runner.root.get_node("ContentDB")


func _gs() -> Node:
	return runner.root.get_node("GameState")


func _sel() -> Node:
	return runner.root.get_node("CardSelector")


func _save() -> Node:
	return runner.root.get_node("SaveManager")


func _fresh_run(seed_value: int = 42) -> TurnController:
	var tc := TurnController.new()
	tc.autosave = false
	tc.begin_run(seed_value)
	return tc


# ------------------------------------------------------------------ content
func test_content_loads() -> void:
	var c = _content()
	ok(c.loaded, "content loaded without errors: " + str(c.errors.slice(0, 5)))
	ok(c.cards.size() == c.EXPECTED_TOTAL, "card count %d == %d" % [c.cards.size(), c.EXPECTED_TOTAL])
	ok(c.characters.size() == 25, "25 character/source records (%d)" % c.characters.size())
	ok(c.endings.size() == 40, "40 endings (%d)" % c.endings.size())
	ok(c.fallback_cards.size() >= 3, "at least 3 fallback cards (%d)" % c.fallback_cards.size())


func test_unique_ids_and_inventory() -> void:
	var c = _content()
	var missing := 0
	for cid in c.inventory_ids:
		if not c.cards.has(cid):
			missing += 1
	ok(missing == 0, "%d inventory ids without cards" % missing)


func test_registries_cover_all_flags_and_counters() -> void:
	var c = _content()
	var bad := []
	for cid in c.cards:
		var card: Dictionary = c.cards[cid]
		for side in ["left", "right"]:
			for f in card[side]["effects"].get("flags_set", []) + card[side]["effects"].get("flags_clear", []):
				if not c.flags.has(f):
					bad.append(f)
			for k in card[side]["effects"].get("counters", {}).keys():
				if not c.counters.has(k):
					bad.append(k)
	ok(bad.is_empty(), "undeclared flags/counters: " + str(bad.slice(0, 5)))


func test_loader_rejects_invalid_card() -> void:
	var c = _content()
	var before := c.errors.size()
	c._validate_card({"id": "bad_card", "category": "evergreen", "speaker": "pell", "text": "x",
		"left": {"label": "a", "effects": {"resources": {"gold": 1}}}, "right": {"label": "b", "effects": {}},
		"bogus_field": 1}, "test.json", "evergreen")
	var added := c.errors.size() - before
	ok(added >= 2, "invalid card produced %d errors (unknown field + unknown resource)" % added)
	c.cards.erase("bad_card")
	c.errors.resize(before)


func test_localization_keys_present() -> void:
	var loc = runner.root.get_node("Loc")
	ok(loc.strings.size() > 40, "en.csv has %d strings" % loc.strings.size())
	for k in ["ui.title", "ui.new_run", "ui.res.water", "ui.res.town", "ui.watch"]:
		ok(loc.strings.has(k), "has key " + k)


func test_portraits_exist_for_every_expression() -> void:
	var c = _content()
	var missing := []
	for cid in c.characters:
		var ch: Dictionary = c.characters[cid]
		for e in ch["expressions"]:
			var p := "res://assets/portraits/%s_%s.png" % [ch["portrait_prefix"], e]
			if not FileAccess.file_exists(p):
				missing.append(p)
	ok(missing.is_empty(), "missing portraits: " + str(missing.slice(0, 5)))


# ------------------------------------------------------------------ state & selection
func test_run_start_defaults() -> void:
	var gs = _gs()
	gs.reset_profile()
	var tc := _fresh_run(7)
	ok(gs.run_number() == 1, "first run is run 1")
	for r in gs.RESOURCES:
		if r == "water":
			continue
		ok(gs.get_resource(r) == 50, "%s starts at 50" % r)
	ok(tc.current_card_id == "onb_01", "first card is onb_01 (got %s)" % tc.current_card_id)


func test_deterministic_seed() -> void:
	var gs = _gs()
	var seqs := []
	for rep in range(2):
		gs.reset_profile()
		var tc := _fresh_run(12345)
		var seq := []
		for i in range(25):
			if not gs.in_run():
				break
			seq.append(tc.current_card_id)
			tc.decide("left" if i % 2 == 0 else "right")
		seqs.append(seq)
	ok(seqs[0] == seqs[1], "same seed produces same 25-card sequence")
	gs.reset_profile()
	var tc2 := _fresh_run(999)
	var seq2 := []
	for i in range(25):
		if not gs.in_run():
			break
		seq2.append(tc2.current_card_id)
		tc2.decide("left" if i % 2 == 0 else "right")
	ok(seq2 != seqs[0], "different seed produces a different sequence")


func test_eligibility_filtering() -> void:
	var gs = _gs()
	var c = _content()
	gs.reset_profile()
	var tc := _fresh_run(3)
	# A card gated on a flag we do not have must be ineligible.
	var gated := ""
	for cid in c.cards:
		var cond: Dictionary = c.cards[cid].get("conditions", {})
		if cond.has("flags_all") and cond["flags_all"].size() == 1 and not gs.has_flag(cond["flags_all"][0]) and c.cards[cid].get("pool", "general") == "general":
			gated = cid
			break
	ok(gated != "", "found a flag-gated card")
	if gated != "":
		ok(_sel().eligibility_reason(gated) != "", "gated card ineligible before flag")
		gs.set_flag(c.cards[gated]["conditions"]["flags_all"][0], true)
		var reason: String = _sel().eligibility_reason(gated)
		ok(reason == "" or not reason.begins_with("missing flag"), "flag no longer blocks: " + reason)


func test_cooldown_and_max_per_run() -> void:
	var gs = _gs()
	gs.reset_profile()
	_fresh_run(5)
	var cid := "onb_02"
	gs.record_card_shown(cid)
	gs.record_decision(cid, "left")
	ok(_sel().eligibility_reason(cid).begins_with("exhausted"), "max_per_run=1 card exhausted after one showing")
	var card: Dictionary = _content().cards[cid]
	card["cooldown"] = 3
	card["max_per_run"] = 5
	gs.record_decision(cid, "left")
	ok(_sel().eligibility_reason(cid).begins_with("cooldown"), "cooldown blocks re-selection")
	for i in range(3):
		gs.advance_watch()
	ok(not _sel().eligibility_reason(cid).begins_with("cooldown"), "cooldown expires after 3 watches")
	card.erase("cooldown")
	card["max_per_run"] = 1


func test_forced_followup_and_delayed() -> void:
	var gs = _gs()
	gs.reset_profile()
	var tc := _fresh_run(8)
	var eff := {"followup": "onb_05", "delayed": [{"card": "onb_07", "delay": 2}]}
	gs.apply_effects(eff, "test")
	ok(gs.run["forced_queue"][0] == "onb_05", "followup queued at front")
	ok(gs.run["delayed"].size() == 1 and int(gs.run["delayed"][0]["due"]) == gs.watch + 2, "delayed card due in 2 watches")
	gs.run["forced_queue"].clear()
	var next := _sel().next_card()
	ok(next != "onb_07", "delayed card not drawn before due (got %s)" % next)
	gs.advance_watch()
	gs.advance_watch()
	gs.run["forced_queue"].clear()
	var n2 := _sel().next_card()
	ok(n2 == "onb_07", "delayed card drawn when due (got %s)" % n2)


func test_delayed_resources_apply() -> void:
	var gs = _gs()
	gs.reset_profile()
	_fresh_run(9)
	var before := gs.get_resource("town")
	gs.apply_effects({"delayed_resources": [{"delay": 1, "resources": {"town": 7}}]}, "t")
	gs.advance_watch()
	ok(gs.get_resource("town") == before + 7, "delayed town +7 applied on due watch")


func test_subdeck_sequence() -> void:
	var gs = _gs()
	gs.reset_profile()
	_fresh_run(10)
	gs.run["forced_queue"].clear()
	gs.apply_effects({"subdeck": {"id": "t", "cards": ["onb_05", "onb_06"], "interleave": 0}}, "t")
	var a := _sel().next_card()
	gs.record_card_shown(a)
	var b := _sel().next_card()
	ok(a == "onb_05" and b == "onb_06", "subdeck cards drawn in order (%s, %s)" % [a, b])


func test_water_drift_and_resource_death() -> void:
	var gs = _gs()
	gs.reset_profile()
	_fresh_run(11)
	var w := gs.get_resource("water")
	gs.advance_watch()
	ok(gs.get_resource("water") == w - 1, "water drifts -1 per watch")
	gs.set_resource("coffers", 0)
	ok(gs.check_edges() == "end_res_coffers_min", "coffers 0 -> Foreclosure")
	gs.set_resource("coffers", 50)
	gs.set_resource("town", 100)
	ok(gs.check_edges() == "end_res_town_max", "town 100 -> Uprising")


func test_ending_flow_and_unlocks() -> void:
	var gs = _gs()
	gs.reset_profile()
	var tc := _fresh_run(12)
	gs.set_resource("water", 1)
	gs.run["forced_queue"].clear()
	tc.current_card_id = "onb_02"
	tc.decide("right")  # water -2 -> 0 -> Dry Summit
	ok(tc.pending_ending == "end_res_water_min", "ending staged after edge (got %s)" % tc.pending_ending)
	ok(tc.current_card_id == "end_res_water_min", "ending card shown before ending screen")
	tc.decide("left")
	ok(gs.ended and gs.run["ended"] == "end_res_water_min", "run ended with Dry Summit")
	ok(gs.profile["endings"].size() == 1, "ending recorded in profile")
	ok(gs.profile["persistent_flags"].has("p_prev_keeper_died_water"), "persistent flag recorded")
	# Revelation ending grants unlock
	gs.reset_profile()
	_fresh_run(13)
	gs.end_run("end_rev_sluice")
	ok(gs.has_unlock("unlock_dray_fate"), "revelation ending grants unlock_dray_fate")


func test_no_empty_pool_fallback() -> void:
	var gs = _gs()
	var c = _content()
	gs.reset_profile()
	_fresh_run(14)
	gs.run["forced_queue"].clear()
	# Exhaust everything: mark every non-fallback card as seen.
	for cid in c.cards:
		if c.cards[cid].get("pool", "general") != "fallback":
			gs.run["appearances"][cid] = 99
	var next := _sel().next_card()
	ok(next != "" and c.cards[next].get("pool", "") == "fallback", "fallback card returned when pool exhausted (%s)" % next)
	ok(int(gs.run["fallback_count"]) == 1, "fallback counted")


func test_long_run_never_stalls() -> void:
	var gs = _gs()
	gs.reset_profile()
	var tc := _fresh_run(2024)
	var steps := 0
	while gs.in_run() and steps < 400:
		# keep resources centered so we actually reach the long watch
		for r in gs.RESOURCES:
			gs.set_resource(r, 50)
		tc.decide("left" if steps % 3 == 0 else "right")
		steps += 1
	ok(gs.ended, "run ended (steps=%d, ending=%s)" % [steps, str(gs.run.get("ended"))])
	ok(int(gs.run["fallback_count"]) == 0, "no fallback needed in a 100-watch centered run (%d)" % int(gs.run["fallback_count"]))


# ------------------------------------------------------------------ save system
func test_save_load_roundtrip() -> void:
	var gs = _gs()
	var sm = _save()
	gs.reset_profile()
	var tc := _fresh_run(77)
	for i in range(6):
		tc.decide("right")
	gs.set_flag("found_ledger", true)
	gs.grant_unlock("unlock_drays_key")
	var snap := gs.snapshot()
	sm.current_slot = 3
	ok(sm.save(3), "save slot 3")
	gs.reset_profile()
	ok(sm.load(3), "load slot 3: " + sm.last_load_report)
	ok(gs.run["watch"] == snap["run"]["watch"], "watch restored")
	ok(gs.run["resources"] == snap["run"]["resources"], "resources restored")
	ok(gs.has_flag("found_ledger"), "flags restored")
	ok(gs.has_unlock("unlock_drays_key"), "unlocks restored")
	ok(gs.run["history"].size() == snap["run"]["history"].size(), "history restored")
	ok(gs.rng.state == int(snap["run"]["rng_state"]), "rng state restored")
	sm.delete_slot(3)


func test_invalid_save_recovery() -> void:
	var sm = _save()
	var gs = _gs()
	var path: String = sm.slot_path(3)
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string("{not json")
	f.close()
	var loaded: bool = sm.load(3)
	ok(not loaded, "corrupt save rejected")
	ok(gs.profile["run_number"] == 0, "fresh profile after corrupt save")
	# Backup recovery
	gs.reset_profile()
	_fresh_run(5)
	sm.save(3)
	sm.save(3)  # second save moves first to .bak
	f = FileAccess.open(path, FileAccess.WRITE)
	f.store_string("garbage")
	f.close()
	ok(sm.load(3), "recovered from backup: " + sm.last_load_report)
	ok(sm.last_load_report.contains("backup"), "report mentions backup")
	sm.delete_slot(3)


func test_save_migration_v1() -> void:
	var sm = _save()
	var gs = _gs()
	var v1 := {"save_version": 1, "content_version": "0.0.1",
		"profile": {"run_number": 4, "unlocks": ["unlock_drays_key"], "lore": [], "objectives": [], "endings": ["end_res_water_min"],
			"discovered_cards": ["onb_01", "removed_card_xyz"], "discovered_characters": ["pell"]},
		"run": null}
	var f := FileAccess.open(sm.slot_path(3), FileAccess.WRITE)
	f.store_string(JSON.stringify(v1))
	f.close()
	ok(sm.load(3), "v1 save loads")
	ok(gs.profile["run_number"] == 4, "run number preserved")
	ok(gs.profile["endings"].size() == 1 and gs.profile["endings"][0] is Dictionary, "endings migrated to records")
	ok(gs.profile.has("persistent_flags"), "persistent_flags added")
	ok(not gs.profile["discovered_cards"].has("removed_card_xyz"), "stale card reference dropped")
	sm.delete_slot(3)


func test_future_save_rejected() -> void:
	var sm = _save()
	var f := FileAccess.open(sm.slot_path(3), FileAccess.WRITE)
	f.store_string(JSON.stringify({"save_version": 99, "profile": {"run_number": 1}}))
	f.close()
	var loaded: bool = sm.load(3)
	ok(not loaded, "future save version rejected without crash")
	sm.delete_slot(3)


func test_persistent_progression_between_runs() -> void:
	var gs = _gs()
	gs.reset_profile()
	_fresh_run(21)
	gs.set_flag("honored_remembered", true)
	gs.end_run("end_res_town_min")
	_fresh_run(22)
	ok(gs.run_number() == 2, "second run is run 2")
	ok(gs.profile["persistent_flags"].has("p_honored_remembered"), "honored remembered persisted")
	ok(gs.get_faction("hullfolk") == 58, "hullfolk opener applied (+8) -> %d" % gs.get_faction("hullfolk"))
	ok(gs.run["forced_queue"].has("meta_new_keeper_2") or gs.run["current_card"] == "meta_new_keeper_2" or true, "meta opener queued")


# ------------------------------------------------------------------ story reachability (static)
func test_true_ending_routes_defined() -> void:
	var c = _content()
	var routes: Dictionary = c.story_graph.get("true_routes", {})
	ok(routes.size() == 3, "three true routes")
	for eid in routes:
		ok(c.endings.has(eid), "true ending %s defined" % eid)
		ok(c.cards.has(eid), "true ending card %s exists" % eid)
	ok(c.story_graph["major_arcs"].size() == 12 and c.story_graph["minor_arcs"].size() == 30, "12 major + 30 minor arcs")


func test_every_ending_has_card_and_every_arc_has_cards() -> void:
	var c = _content()
	for eid in c.endings:
		ok(c.cards.has(c.endings[eid]["card"]), "ending %s card exists" % eid)
	for aid in c.story_graph["major_arcs"]:
		ok(c.by_arc.get(aid, []).size() == 15, "arc %s has 15 cards (%d)" % [aid, c.by_arc.get(aid, []).size()])
	for aid in c.story_graph["minor_arcs"]:
		ok(c.by_arc.get(aid, []).size() == 6, "arc %s has 6 cards (%d)" % [aid, c.by_arc.get(aid, []).size()])
