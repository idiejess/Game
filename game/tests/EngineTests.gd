extends RefCounted
## Engine tests. Each test_* method uses runner.check(cond, current, message).
## Autoloads (ContentDB, GameState, CardSelector, SaveManager, Loc) are available as singletons.

var runner
var current := ""


func ok(cond: bool, msg: String) -> void:
	runner.check(cond, current, msg)


func _fresh_run(seed_value: int = 42) -> TurnController:
	var tc := TurnController.new()
	tc.autosave = false
	tc.begin_run(seed_value)
	return tc


# ------------------------------------------------------------------ content
func test_content_loads() -> void:
	ok(ContentDB.loaded, "content loaded without errors: " + str(ContentDB.errors.slice(0, 5)))
	ok(ContentDB.cards.size() == ContentDB.EXPECTED_TOTAL, "card count %d == %d" % [ContentDB.cards.size(), ContentDB.EXPECTED_TOTAL])
	ok(ContentDB.characters.size() == 25, "25 character/source records (%d)" % ContentDB.characters.size())
	ok(ContentDB.endings.size() == 40, "40 endings (%d)" % ContentDB.endings.size())
	ok(ContentDB.fallback_cards.size() >= 3, "at least 3 fallback cards (%d)" % ContentDB.fallback_cards.size())


func test_unique_ids_and_inventory() -> void:
	var missing := 0
	for cid in ContentDB.inventory_ids:
		if not ContentDB.cards.has(cid):
			missing += 1
	ok(missing == 0, "%d inventory ids without cards" % missing)
	ok(ContentDB.inventory_ids.size() == 1000, "inventory has 1000 ids")


func test_registries_cover_all_flags_and_counters() -> void:
	var bad: Array = []
	for cid in ContentDB.cards:
		var card: Dictionary = ContentDB.cards[cid]
		for side in ["left", "right"]:
			var eff: Dictionary = card[side]["effects"]
			for f in eff.get("flags_set", []) + eff.get("flags_clear", []):
				if not ContentDB.flags.has(f):
					bad.append(f)
			for k in eff.get("counters", {}).keys():
				if not ContentDB.counters.has(k):
					bad.append(k)
	ok(bad.is_empty(), "undeclared flags/counters: " + str(bad.slice(0, 5)))


func test_loader_rejects_invalid_card() -> void:
	var before: int = ContentDB.errors.size()
	ContentDB._validate_card({"id": "bad_card", "category": "evergreen", "speaker": "pell", "text": "x",
		"left": {"label": "a", "effects": {"resources": {"gold": 1}}}, "right": {"label": "b", "effects": {}},
		"bogus_field": 1}, "test.json", "evergreen")
	var added: int = ContentDB.errors.size() - before
	ok(added >= 2, "invalid card produced %d errors (unknown field + unknown resource)" % added)
	ContentDB.cards.erase("bad_card")
	ContentDB.errors.resize(before)


func test_localization_keys_present() -> void:
	ok(Loc.strings.size() > 40, "en localization has %d strings" % Loc.strings.size())
	for k in ["ui.title", "ui.new_run", "ui.res.water", "ui.res.town", "ui.watch"]:
		ok(Loc.strings.has(k), "has key " + k)
	ok(Loc.strings.has("card.onb_01.text"), "card localization mirror present")


func test_accessibility_settings() -> void:
	var saved := Settings.data.duplicate(true)
	Settings.data["reduced_motion"] = true
	ok(Settings.motion_scale() == 0.0, "reduced motion zeroes motion scale")
	Settings.data["reduced_motion"] = false
	ok(Settings.motion_scale() == 1.0, "motion scale restored")
	Settings.data["text_scale"] = 1.6
	ok(UITheme.scaled(30) == 48, "scaled() honours text scale (%d)" % UITheme.scaled(30))
	for hc in [false, true]:
		var t := UITheme.build(1.6, hc)
		ok(t.default_font_size == int(UITheme.BASE_FONT * 1.6), "theme font size scales (hc=%s)" % hc)
		var fg: Color = t.get_color("font_color", "Label")
		var bg: Color = (t.get_stylebox("panel", "PanelContainer") as StyleBoxFlat).bg_color
		var contrast: float = abs(fg.get_luminance() - bg.get_luminance())
		ok(contrast > 0.5, "label/panel luminance contrast %.2f (hc=%s)" % [contrast, hc])
	for sfx in AudioBus._sub_keys:
		var k: String = "ui." + AudioBus._sub_keys[sfx].trim_prefix("ui.")
		ok(Loc.strings.has(k), "subtitle text exists for " + sfx)
	for key in ["text_scale", "high_contrast", "reduced_motion", "screen_shake", "show_buttons", "confirm_decisions", "show_exact_effects", "subtitles"]:
		ok(Settings.DEFAULTS.has(key), "settings default for " + key)
	Settings.data = saved


func test_portraits_exist_for_every_expression() -> void:
	var missing: Array = []
	for cid in ContentDB.characters:
		var ch: Dictionary = ContentDB.characters[cid]
		for e in ch["expressions"]:
			var p: String = "res://assets/portraits/%s_%s.png" % [ch["portrait_prefix"], e]
			if not FileAccess.file_exists(p):
				missing.append(p)
	ok(missing.is_empty(), "missing portraits: " + str(missing.slice(0, 5)))


func test_audio_assets_exist() -> void:
	var missing: Array = []
	for id in ["sfx_card_drag", "sfx_card_commit", "sfx_res_up", "sfx_res_down", "sfx_warning", "sfx_death", "sfx_unlock", "sfx_telegram", "sfx_revelation", "sfx_success", "mus_title", "mus_ambient", "mus_crisis", "mus_ending_fail", "mus_ending_true", "mus_ending_ordinary"]:
		if AudioBus.asset_path(id) == "":
			missing.append(id)
	ok(missing.is_empty(), "missing audio placeholders: " + str(missing))


# ------------------------------------------------------------------ state & selection
func test_run_start_defaults() -> void:
	GameState.reset_profile()
	var tc := _fresh_run(7)
	ok(GameState.run_number() == 1, "first run is run 1")
	for r in GameState.RESOURCES:
		if r == "water":
			continue
		ok(GameState.get_resource(r) == 50, "%s starts at 50" % r)
	ok(tc.current_card_id == "onb_01", "first card is onb_01 (got %s)" % tc.current_card_id)


func test_deterministic_seed() -> void:
	var seqs: Array = []
	for rep in range(2):
		GameState.reset_profile()
		var tc := _fresh_run(12345)
		var seq: Array = []
		for i in range(25):
			if not GameState.in_run():
				break
			seq.append(tc.current_card_id)
			tc.decide("left" if i % 2 == 0 else "right")
		seqs.append(seq)
	ok(seqs[0] == seqs[1], "same seed produces same 25-card sequence")
	GameState.reset_profile()
	var tc2 := _fresh_run(999)
	var seq2: Array = []
	for i in range(25):
		if not GameState.in_run():
			break
		seq2.append(tc2.current_card_id)
		tc2.decide("left" if i % 2 == 0 else "right")
	ok(seq2 != seqs[0], "different seed produces a different sequence")


func test_eligibility_filtering() -> void:
	GameState.reset_profile()
	_fresh_run(3)
	var reason: String = CardSelector.eligibility_reason("ma02_01")
	ok(reason != "", "flag-gated arc card ineligible at start: " + reason)
	GameState.set_flag("met_mirren", true)
	GameState.run["relationships"]["mirren"] = 60
	GameState.run["watch"] = 10
	ok(CardSelector.eligibility_reason("ma02_01") == "", "ma02_01 eligible once conditions met: " + CardSelector.eligibility_reason("ma02_01"))
	ok(CardSelector.eligibility_reason("end_true_river") != "", "ending-pool card never eligible via selection")
	ok(CardSelector.eligibility_reason("ma01_15") != "", "forced-pool card never eligible via selection")


func test_cooldown_and_max_per_run() -> void:
	GameState.reset_profile()
	_fresh_run(5)
	var cid := "onb_02"
	GameState.record_card_shown(cid)
	GameState.record_decision(cid, "left")
	ok(CardSelector.eligibility_reason(cid).begins_with("exhausted"), "max_per_run=1 card exhausted after one showing")
	var card: Dictionary = ContentDB.cards[cid]
	card["cooldown"] = 3
	card["max_per_run"] = 5
	GameState.record_decision(cid, "left")
	ok(CardSelector.eligibility_reason(cid).begins_with("cooldown"), "cooldown blocks re-selection")
	for i in range(3):
		GameState.advance_watch()
	ok(not CardSelector.eligibility_reason(cid).begins_with("cooldown"), "cooldown expires after 3 watches")
	card.erase("cooldown")
	card["max_per_run"] = 1


func test_forced_followup_and_delayed() -> void:
	GameState.reset_profile()
	_fresh_run(8)
	GameState.apply_effects({"followup": "onb_05", "delayed": [{"card": "onb_07", "delay": 2}]}, "test")
	ok(GameState.run["forced_queue"][0] == "onb_05", "followup queued at front")
	ok(GameState.run["delayed"].size() == 1 and int(GameState.run["delayed"][0]["due"]) == GameState.watch + 2, "delayed card due in 2 watches")
	GameState.run["forced_queue"].clear()
	var next: String = CardSelector.next_card()
	ok(next != "onb_07", "delayed card not drawn before due (got %s)" % next)
	GameState.advance_watch()
	GameState.advance_watch()
	GameState.run["forced_queue"].clear()
	var n2: String = CardSelector.next_card()
	ok(n2 == "onb_07", "delayed card drawn when due (got %s)" % n2)


func test_delayed_resources_apply() -> void:
	GameState.reset_profile()
	_fresh_run(9)
	var before: int = GameState.get_resource("town")
	GameState.apply_effects({"delayed_resources": [{"delay": 1, "resources": {"town": 7}}]}, "t")
	GameState.advance_watch()
	ok(GameState.get_resource("town") == before + 7, "delayed town +7 applied on due watch")


func test_subdeck_sequence() -> void:
	GameState.reset_profile()
	_fresh_run(10)
	GameState.run["forced_queue"].clear()
	GameState.apply_effects({"subdeck": {"id": "t", "cards": ["onb_05", "onb_06"], "interleave": 0}}, "t")
	var a: String = CardSelector.next_card()
	GameState.record_card_shown(a)
	var b: String = CardSelector.next_card()
	ok(a == "onb_05" and b == "onb_06", "subdeck cards drawn in order (%s, %s)" % [a, b])


func test_water_drift_and_resource_death() -> void:
	GameState.reset_profile()
	_fresh_run(11)
	var w: int = GameState.get_resource("water")
	GameState.advance_watch()
	ok(GameState.get_resource("water") == w - 1, "water drifts -1 per watch")
	GameState.set_resource("traffic", GameState.TRAFFIC_QUIET)
	w = GameState.get_resource("water")
	GameState.advance_watch()
	ok(GameState.get_resource("water") == w, "quiet gate: pound holds (drift 0)")
	GameState.set_resource("traffic", GameState.TRAFFIC_BUSY)
	w = GameState.get_resource("water")
	GameState.advance_watch()
	ok(GameState.get_resource("water") == w - 2, "busy gate: pound loses 2")
	GameState.set_resource("traffic", 50)
	GameState.set_flag("sluice_rebuilt", true)
	w = GameState.get_resource("water")
	GameState.advance_watch()
	ok(GameState.get_resource("water") == w, "rebuilt sluice stops drift")
	GameState.set_flag("sluice_rebuilt", false)
	GameState.set_resource("coffers", 0)
	ok(GameState.check_edges() == "end_res_coffers_min", "coffers 0 -> Foreclosure")
	GameState.set_resource("coffers", 50)
	GameState.set_resource("town", 100)
	ok(GameState.check_edges() == "end_res_town_max", "town 100 -> Uprising")


func test_ending_flow_and_unlocks() -> void:
	GameState.reset_profile()
	var tc := _fresh_run(12)
	GameState.set_resource("water", 1)
	GameState.run["forced_queue"].clear()
	tc.current_card_id = "onb_02"
	tc.decide("right")  # water -2 -> 0 -> Dry Summit
	ok(tc.pending_ending == "end_res_water_min", "ending staged after edge (got %s)" % tc.pending_ending)
	ok(tc.current_card_id == "end_res_water_min", "ending card shown before ending screen")
	tc.decide("left")
	ok(GameState.ended and GameState.run["ended"] == "end_res_water_min", "run ended with Dry Summit")
	ok(GameState.profile["endings"].size() == 1, "ending recorded in profile")
	ok(GameState.profile["persistent_flags"].has("p_prev_keeper_died_water"), "persistent flag recorded")
	GameState.reset_profile()
	_fresh_run(13)
	GameState.end_run("end_rev_sluice")
	ok(GameState.has_unlock("unlock_dray_fate"), "revelation ending grants unlock_dray_fate")


func test_data_driven_ending_triggers() -> void:
	GameState.reset_profile()
	var tc := _fresh_run(16)
	# Revelation variant of a resource death takes priority over the plain death.
	GameState.set_flag("sluice_house_opened", true)
	GameState.set_resource("water", 0)
	ok(GameState.check_edges() == "end_rev_sluice", "water death with sluice house opened -> Into the Dark Water (got %s)" % GameState.check_edges())
	GameState.set_flag("sluice_house_opened", false)
	ok(GameState.check_edges() == "end_res_water_min", "plain water death otherwise")
	GameState.set_resource("water", 50)
	# Crisis ending from flags + resources.
	ok(GameState.check_triggered_endings() == "", "no triggered ending in a calm run")
	GameState.set_flag("riot_brewing", true)
	GameState.set_resource("town", 10)
	ok(GameState.check_triggered_endings() == "end_crisis_riot", "riot brewing at town 10 -> The Riot (got %s)" % GameState.check_triggered_endings())
	GameState.set_flag("riot_brewing", false)
	GameState.set_resource("town", 50)
	# False ending respects watch_min.
	for f in ["vosk_enemy", "hesse_has_story", "pressed_by_hesse"]:
		GameState.set_flag(f, true)
	ok(GameState.check_triggered_endings() == "", "Dray's Killer needs watch >= 40 (watch %d)" % GameState.watch)
	GameState.run["watch"] = 45
	ok(GameState.check_triggered_endings() == "end_false_killer", "Dray's Killer fires after watch 40")
	for f in ["vosk_enemy", "hesse_has_story", "pressed_by_hesse"]:
		GameState.set_flag(f, false)
	# Long-watch priority order and fallback.
	ok(GameState.long_watch_ending() == "end_ord_long_watch", "plain retirement fallback")
	GameState.set_resource("town", 80)
	ok(GameState.long_watch_ending() == "end_ord_towns_keeper", "Town's Keeper when town high")
	GameState.set_flag("jubilee_held", true)
	ok(GameState.long_watch_ending() == "end_ord_jubilee", "Jubilee outranks Town's Keeper")
	# The triggered ending flows through the controller: its card is staged, then the run ends.
	GameState.set_flag("jubilee_held", false)
	GameState.set_resource("town", 50)
	GameState.set_flag("frost", true)
	GameState.set_resource("coffers", 20)
	GameState.set_resource("traffic", 25)
	GameState.run["forced_queue"].clear()
	tc.current_card_id = "onb_03"
	tc.decide("left")
	ok(tc.pending_ending == "end_crisis_frost", "frost closure staged via controller (got %s)" % tc.pending_ending)
	ok(tc.current_card_id == "end_crisis_frost", "frost ending card shown first")
	tc.decide("right")
	ok(GameState.run["ended"] == "end_crisis_frost", "run ended with The Frost Closure")


func test_true_ending_trigger_from_card() -> void:
	GameState.reset_profile()
	var tc := _fresh_run(14)
	GameState.grant_unlock("unlock_cut_map")
	for f in ["allies_gathered", "sluice_rebuilt", "route_river"]:
		GameState.set_flag(f, true)
	GameState.set_arc("MA12", 4, "active")
	GameState.run["factions"]["hullfolk"] = 70
	GameState.set_resource("town", 50)
	ok(CardSelector.eligibility_reason("ma12_13") == "", "TE1 finale eligible under its conditions: " + CardSelector.eligibility_reason("ma12_13"))
	GameState.run["forced_queue"].clear()
	tc.current_card_id = "ma12_13"
	tc.decide("left")
	ok(tc.pending_ending == "end_true_river", "true ending staged from card effect (got %s)" % tc.pending_ending)
	tc.decide("left")
	ok(GameState.run["ended"] == "end_true_river", "run ended with The River Returned")
	ok(GameState.profile["persistent_flags"].has("p_true_ending_seen"), "true ending persisted")


func test_no_empty_pool_fallback() -> void:
	GameState.reset_profile()
	_fresh_run(15)
	GameState.run["forced_queue"].clear()
	for cid in ContentDB.cards:
		if ContentDB.cards[cid].get("pool", "general") != "fallback":
			GameState.run["appearances"][cid] = 99
	var next: String = CardSelector.next_card()
	ok(next != "" and ContentDB.cards[next].get("pool", "") == "fallback", "fallback card returned when pool exhausted (%s)" % next)
	ok(int(GameState.run["fallback_count"]) == 1, "fallback counted")


func test_long_run_never_stalls() -> void:
	GameState.reset_profile()
	var tc := _fresh_run(2024)
	var steps := 0
	while GameState.in_run() and steps < 400:
		for r in GameState.RESOURCES:
			GameState.set_resource(r, 50)
		tc.decide("left" if steps % 3 == 0 else "right")
		steps += 1
	ok(GameState.ended, "run ended (steps=%d, ending=%s)" % [steps, str(GameState.run.get("ended"))])
	ok(int(GameState.run["fallback_count"]) == 0, "no fallback needed in a 100-watch centered run (%d)" % int(GameState.run["fallback_count"]))


func test_selection_variety() -> void:
	GameState.reset_profile()
	var tc := _fresh_run(777)
	var seen := {}
	var steps := 0
	while GameState.in_run() and steps < 120:
		for r in GameState.RESOURCES:
			GameState.set_resource(r, 50)
		seen[tc.current_card_id] = true
		tc.decide("right")
		steps += 1
	ok(seen.size() >= 60, "at least 60 distinct cards in 100 watches (%d)" % seen.size())


# ------------------------------------------------------------------ parity with the Python simulator
## Reference produced by `python3 tools/sim_trace.py --seed 12345 --steps 40`. If this fails after a
## deliberate rules change, update both engines and regenerate the reference in one commit.
const PY_TRACE_12345 := "onb_01 evg_company_orders_01 evg_order_01 onb_12 onb_15 onb_28 evg_cargo_09 onb_11 onb_13 onb_16 onb_20 evg_order_10 onb_26 rel_wren_01 evg_order_15 mi10_1 evg_tolls_08 evg_strangers_04 rel_wren_03 evg_tolls_03 rel_vane_01 res_water_09 ma10_01 evg_maintenance_10 evg_strangers_10 evg_cargo_13 evg_order_13 ma10_03 cri_dry_04 cri_dry_01 evg_company_orders_11 evg_cargo_01 evg_weather_11 evg_company_orders_06 ma04_01 rel_vane_06 evg_hullfolk_12 mi16_1 evg_company_orders_02 rel_vane_03"
const PY_RES_12345 := {"water": 3, "traffic": 40, "coffers": 53, "company": 67, "town": 63}


func test_engine_matches_python_simulator() -> void:
	GameState.reset_profile()
	var tc := _fresh_run(12345)
	var seq: Array = []
	for i in range(40):
		if not GameState.in_run():
			break
		seq.append(tc.current_card_id)
		tc.decide("left" if i % 2 == 0 else "right")
	var expected := PY_TRACE_12345.split(" ")
	var first_diff := -1
	for i in range(min(seq.size(), expected.size())):
		if seq[i] != expected[i]:
			first_diff = i
			break
	ok(seq.size() == expected.size() and first_diff < 0, "40-card trace equals Python simulator (first diff at %d: %s)" % [first_diff, str(seq.slice(max(0, first_diff - 1), first_diff + 2)) if first_diff >= 0 else "none"])
	var same := true
	for r in GameState.RESOURCES:
		if GameState.get_resource(r) != int(PY_RES_12345[r]):
			same = false
	ok(same, "resources after 40 watches equal Python simulator %s vs %s" % [str(GameState.run["resources"]), str(PY_RES_12345)])


# ------------------------------------------------------------------ save system
func test_save_load_roundtrip() -> void:
	GameState.reset_profile()
	var tc := _fresh_run(77)
	for i in range(6):
		tc.decide("right")
	GameState.set_flag("found_ledger", true)
	GameState.grant_unlock("unlock_drays_key")
	var snap: Dictionary = GameState.snapshot()
	SaveManager.current_slot = 3
	ok(SaveManager.save(3), "save slot 3")
	GameState.reset_profile()
	ok(SaveManager.load(3), "load slot 3: " + SaveManager.last_load_report)
	ok(GameState.run["watch"] == snap["run"]["watch"], "watch restored")
	ok(GameState.run["resources"] == snap["run"]["resources"], "resources restored")
	ok(GameState.has_flag("found_ledger"), "flags restored")
	ok(GameState.has_unlock("unlock_drays_key"), "unlocks restored")
	ok(GameState.run["history"].size() == snap["run"]["history"].size(), "history restored")
	ok(GameState.rng.state == int(snap["run"]["rng_state"]), "rng state restored")
	SaveManager.delete_slot(3)


## Full-state regression: every run/profile field survives a save/load, numbers stay ints, and the
## selection sequence after loading equals the sequence of an uninterrupted run (RNG continuation).
func test_save_load_full_state_and_rng_continuation() -> void:
	GameState.reset_profile()
	var tc := _fresh_run(4040)
	for i in range(8):
		tc.decide("left" if i % 2 == 0 else "right")
	GameState.apply_effects({
		"relationships": {"vosk": 7}, "factions": {"hullfolk": -6},
		"flags_set": ["found_ledger"], "counters": {"cipher_progress": 2},
		"delayed": [{"card": "onb_07", "delay": 5}],
		"delayed_resources": [{"delay": 4, "resources": {"town": 3}, "message": "late"}],
		"followup": "onb_06", "arc": {"MA02": {"stage": 2, "status": "active"}},
		"unlocks": ["unlock_drays_key"], "lore": ["lore_test"],
	}, "test")
	GameState.run["cooldowns"]["onb_02"] = 4
	GameState.profile["endings"].append({"id": "end_res_town_min", "run": 1, "watch": 3})
	GameState.add_persistent_counter("p_keepers_lost", 2)
	GameState.set_flag("p_told_mirren", true)
	var snap: Dictionary = GameState.snapshot()
	var current: String = tc.current_card_id
	ok(SaveManager.save(3), "save slot 3")
	# Uninterrupted continuation reference.
	var ref_seq: Array = []
	for i in range(12):
		if not GameState.in_run():
			break
		ref_seq.append(tc.current_card_id)
		tc.decide("right")
	# Reload and replay the same decisions.
	GameState.reset_profile()
	ok(SaveManager.load(3), "load slot 3: " + SaveManager.last_load_report)
	var r: Dictionary = GameState.run
	var s: Dictionary = snap["run"]
	ok(r["watch"] == s["watch"] and typeof(r["watch"]) == TYPE_INT, "watch restored as int")
	ok(r["seed"] == s["seed"], "seed restored")
	ok(r["resources"] == s["resources"], "resources restored")
	ok(r["relationships"] == s["relationships"], "relationships restored")
	ok(r["factions"] == s["factions"], "factions restored")
	ok(r["flags"] == s["flags"], "flags restored")
	ok(r["counters"] == s["counters"], "counters restored")
	ok(r["history"] == s["history"], "history restored")
	ok(r["cooldowns"] == s["cooldowns"], "cooldowns restored")
	ok(r["delayed"] == s["delayed"], "delayed cards restored")
	ok(r["delayed_resources"] == s["delayed_resources"], "delayed resources restored")
	ok(r["forced_queue"] == s["forced_queue"], "forced queue restored")
	ok(r["arcs"] == s["arcs"], "active arcs restored")
	ok(r["appearances"] == s["appearances"], "appearances restored")
	ok(r["current_card"] == current, "current card restored (%s)" % str(r["current_card"]))
	ok(GameState.rng.state == int(s["rng_state"]), "rng state restored")
	var p: Dictionary = GameState.profile
	ok(p["run_number"] == 1 and typeof(p["run_number"]) == TYPE_INT, "run number restored as int")
	ok(p["endings"] == snap["profile"]["endings"], "endings restored")
	ok(p["unlocks"].has("unlock_drays_key") and p["lore"].has("lore_test"), "unlocks and lore restored")
	ok(p["persistent_counters"] == snap["profile"]["persistent_counters"], "persistent counters restored")
	ok(p["persistent_flags"] == snap["profile"]["persistent_flags"], "persistent flags restored")
	ok(p["discovered_cards"] == snap["profile"]["discovered_cards"], "discovered cards restored")
	ok(p["total_watches"] == snap["profile"]["total_watches"], "total watches restored")
	var tc2 := TurnController.new()
	tc2.autosave = false
	tc2.resume_run()
	var seq: Array = []
	for i in range(12):
		if not GameState.in_run():
			break
		seq.append(tc2.current_card_id)
		tc2.decide("right")
	ok(seq == ref_seq, "card sequence after load equals uninterrupted sequence")
	SaveManager.delete_slot(3)


func test_save_ended_run_and_persistent_between_sessions() -> void:
	GameState.reset_profile()
	var tc := _fresh_run(4141)
	GameState.set_flag("honored_remembered", true)
	GameState.end_run("end_res_town_min")
	ok(SaveManager.save(3), "ended run saved")
	GameState.reset_profile()
	ok(SaveManager.load(3), "loaded after ending")
	ok(not GameState.in_run() and GameState.run.is_empty(), "ended run is not resumed")
	ok(GameState.profile["run_number"] == 1 and GameState.has_ending("end_res_town_min"), "profile keeps run number and ending")
	ok(GameState.profile["persistent_flags"].has("p_honored_remembered"), "persistent flag survives save")
	var tc2 := _fresh_run(4142)
	ok(GameState.run_number() == 2 and GameState.get_faction("hullfolk") == 58, "next run applies persistent opener")
	SaveManager.delete_slot(3)


func test_save_ignores_removed_content_references() -> void:
	GameState.reset_profile()
	var tc := _fresh_run(4343)
	tc.decide("left")  # watch must be > 0 for the loader to resume the run
	GameState.run["forced_queue"].append("card_that_no_longer_exists")
	GameState.run["delayed"].append({"card": "gone_card", "due": 3})
	GameState.run["cooldowns"]["gone_card"] = 2
	GameState.profile["discovered_cards"].append("gone_card")
	SaveManager.save(3)
	GameState.reset_profile()
	ok(SaveManager.load(3), "save with stale references loads")
	ok(not GameState.run["forced_queue"].has("card_that_no_longer_exists"), "stale forced card dropped")
	ok(GameState.run["delayed"].is_empty(), "stale delayed card dropped")
	ok(not GameState.run["cooldowns"].has("gone_card"), "stale cooldown dropped")
	ok(not GameState.profile["discovered_cards"].has("gone_card"), "stale discovered card dropped")
	SaveManager.delete_slot(3)


func test_invalid_save_recovery() -> void:
	var path: String = SaveManager.slot_path(3)
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string("{not json")
	f.close()
	var loaded: bool = SaveManager.load(3)
	ok(not loaded, "corrupt save rejected")
	ok(GameState.profile["run_number"] == 0, "fresh profile after corrupt save")
	GameState.reset_profile()
	_fresh_run(5)
	SaveManager.save(3)
	SaveManager.save(3)
	f = FileAccess.open(path, FileAccess.WRITE)
	f.store_string("garbage")
	f.close()
	ok(SaveManager.load(3), "recovered from backup: " + SaveManager.last_load_report)
	ok(SaveManager.last_load_report.contains("backup"), "report mentions backup")
	SaveManager.delete_slot(3)


func test_save_migration_v1() -> void:
	var v1 := {"save_version": 1, "content_version": "0.0.1",
		"profile": {"run_number": 4, "unlocks": ["unlock_drays_key"], "lore": [], "objectives": [], "endings": ["end_res_water_min"],
			"discovered_cards": ["onb_01", "removed_card_xyz"], "discovered_characters": ["pell"]},
		"run": null}
	var f := FileAccess.open(SaveManager.slot_path(3), FileAccess.WRITE)
	f.store_string(JSON.stringify(v1))
	f.close()
	ok(SaveManager.load(3), "v1 save loads")
	ok(GameState.profile["run_number"] == 4, "run number preserved")
	ok(GameState.profile["endings"].size() == 1 and GameState.profile["endings"][0] is Dictionary, "endings migrated to records")
	ok(GameState.profile.has("persistent_flags"), "persistent_flags added")
	ok(not GameState.profile["discovered_cards"].has("removed_card_xyz"), "stale card reference dropped")
	SaveManager.delete_slot(3)


func test_future_save_rejected() -> void:
	var f := FileAccess.open(SaveManager.slot_path(3), FileAccess.WRITE)
	f.store_string(JSON.stringify({"save_version": 99, "profile": {"run_number": 1}}))
	f.close()
	var loaded: bool = SaveManager.load(3)
	ok(not loaded, "future save version rejected without crash")
	SaveManager.delete_slot(3)


func test_persistent_progression_between_runs() -> void:
	GameState.reset_profile()
	_fresh_run(21)
	GameState.set_flag("honored_remembered", true)
	GameState.end_run("end_res_town_min")
	_fresh_run(22)
	ok(GameState.run_number() == 2, "second run is run 2")
	ok(GameState.profile["persistent_flags"].has("p_honored_remembered"), "honored remembered persisted")
	ok(GameState.get_faction("hullfolk") == 58, "hullfolk opener applied (+8) -> %d" % GameState.get_faction("hullfolk"))
	var queued: bool = GameState.run["forced_queue"].has("meta_new_keeper_2") or GameState.run["current_card"] == "meta_new_keeper_2"
	ok(queued, "meta opener queued on run 2")


# ------------------------------------------------------------------ story structure
func test_true_ending_routes_defined() -> void:
	var routes: Dictionary = ContentDB.story_graph.get("true_routes", {})
	ok(routes.size() == 3, "three true routes")
	for eid in routes:
		ok(ContentDB.endings.has(eid), "true ending %s defined" % eid)
		ok(ContentDB.cards.has(eid), "true ending card %s exists" % eid)
	ok(ContentDB.story_graph["major_arcs"].size() == 12 and ContentDB.story_graph["minor_arcs"].size() == 30, "12 major + 30 minor arcs")


func test_every_ending_has_card_and_every_arc_has_cards() -> void:
	for eid in ContentDB.endings:
		ok(ContentDB.cards.has(ContentDB.endings[eid]["card"]), "ending %s card exists" % eid)
	for aid in ContentDB.story_graph["major_arcs"]:
		ok(ContentDB.by_arc.get(aid, []).size() == 15, "arc %s has 15 cards (%d)" % [aid, ContentDB.by_arc.get(aid, []).size()])
	for aid in ContentDB.story_graph["minor_arcs"]:
		ok(ContentDB.by_arc.get(aid, []).size() == 6, "arc %s has 6 cards (%d)" % [aid, ContentDB.by_arc.get(aid, []).size()])
