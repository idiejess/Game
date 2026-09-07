extends Node
## Scripted end-to-end playtest through the real Main scene (UI layer, not just the engine).
## Plays: content warning -> title -> new run -> decisions via the same path buttons/keys use ->
## pause/settings/history/objectives -> save, quit to title, continue -> play to an ending ->
## ending screen -> second Keeper (meta card, Ledger carry-over) -> archive/ending history.
## Writes reports/validation/end_to_end_playtest.json. Exit 1 on any failed check.
##   godot --headless --path . game/tests/Playtest.tscn [-- --slot 3 --seed 4242 --max-watches 400]

var main: Control
var checks: Array = []
var failures := 0
var log_lines: Array = []
var slot := 3
var seed_value := 4242
var max_watches := 400
var endings_seen: Array = []
var subtitles_seen := 0
var unlocks_seen := 0


func _arg(name: String, default: String) -> String:
	var args := OS.get_cmdline_user_args()
	for i in range(args.size()):
		if args[i] == name and i + 1 < args.size():
			return args[i + 1]
	return default


func ok(cond: bool, msg: String) -> void:
	checks.append({"ok": cond, "check": msg})
	if not cond:
		failures += 1
		printerr("PLAYTEST FAIL: " + msg)


func note(s: String) -> void:
	log_lines.append(s)
	print(s)


func _frames(n: int) -> void:
	for i in range(n):
		await get_tree().process_frame


## Card commits run on tweens measured in seconds, so wait for wall time, not frames.
func _settle(seconds: float = 0.3) -> void:
	await get_tree().create_timer(seconds).timeout
	await get_tree().process_frame


func _until(pred: Callable, timeout_s: float = 2.0) -> void:
	var t := 0.0
	while not pred.call() and t < timeout_s:
		await get_tree().process_frame
		t += get_process_delta_time()
	await get_tree().process_frame


func _ready() -> void:
	slot = int(_arg("--slot", "3"))
	seed_value = int(_arg("--seed", "4242"))
	max_watches = int(_arg("--max-watches", "400"))
	var saved_settings: Dictionary = Settings.data.duplicate(true)
	Settings.data = Settings.DEFAULTS.duplicate(true)
	Settings.data["reduced_motion"] = true
	Settings.data["music_volume"] = 0.0
	Settings.data["sfx_volume"] = 0.0
	Settings.changed.emit()
	SaveManager.current_slot = slot
	SaveManager.delete_slot(slot)
	GameState.reset_profile()

	main = load("res://game/scripts/Main.gd").new()
	main.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(main)
	# Main._ready loads slot 1 (the player's profile); isolate the playtest from it.
	GameState.reset_profile()
	SaveManager.current_slot = slot
	AudioBus.subtitle.connect(func(_t): subtitles_seen += 1)
	GameState.unlock_gained.connect(func(_u): unlocks_seen += 1)
	main.turn.ending_fired.connect(func(e): endings_seen.append(e))
	await _frames(3)

	# 1. First launch: content warning, then title.
	ok(main._current_screen == "content_warning", "first launch shows content warning (got %s)" % main._current_screen)
	_press_first_button()
	await _frames(2)
	ok(Settings.get_value("content_warnings_seen") == true, "content warning acknowledged persists")
	ok(main._current_screen == "title", "title after content warning (got %s)" % main._current_screen)

	# 2. New run through the title button path.
	main.start_new_run(seed_value)
	await _frames(3)
	ok(GameState.in_run(), "run started")
	ok(main.turn.current_card_id == "onb_01", "first card is onb_01 (got %s)" % main.turn.current_card_id)
	ok(main.card_view.visible and not main.card_view.card.is_empty(), "card view shows a card")
	for r in main.RESOURCES:
		ok(int(main.meters[r].bar.value) == GameState.get_resource(r), "meter %s matches state" % r)

	# 3. Decisions via the same entry point as buttons/keys, with preview first.
	var before_watch := GameState.watch
	main._preview("left")
	await _frames(2)
	main._clear_preview()
	main._request_decision("left")
	await _settle()
	ok(GameState.watch == before_watch + 1, "decision via _request_decision advanced the watch")
	ok(GameState.run["history"].size() == 1, "history recorded the decision")
	# Confirm-decisions setting requires a second press.
	Settings.data["confirm_decisions"] = true
	before_watch = GameState.watch
	main._request_decision("right")
	await _settle()
	ok(GameState.watch == before_watch, "confirm mode: first press does not commit")
	ok(main.message_label.text != "", "confirm mode shows a hint")
	main._request_decision("right")
	await _settle()
	ok(GameState.watch == before_watch + 1, "confirm mode: second press commits")
	Settings.data["confirm_decisions"] = false

	# 3b. With motion enabled, the next card must come back on screen after the fly-out commit
	# (regression: it stayed a viewport off to the side, invisible, though input still worked).
	Settings.data["reduced_motion"] = false
	Settings.changed.emit()
	before_watch = GameState.watch
	main._request_decision("left")
	await _settle(1.0)
	ok(GameState.watch == before_watch + 1, "motion on: decision committed")
	ok(main.card_view.position.is_equal_approx(main.card_view._origin), "motion on: next card is back at its origin (pos %s, origin %s)" % [str(main.card_view.position), str(main.card_view._origin)])
	ok(main.card_view.modulate.a > 0.99, "motion on: next card is fully visible (alpha %.2f)" % main.card_view.modulate.a)
	# Pointer drag past the threshold commits (regression: drag distance was always 0).
	before_watch = GameState.watch
	var cv: CardView = main.card_view
	var start: Vector2 = cv.position + cv.size / 2.0
	var threshold: float = cv.get_viewport_rect().size.x * CardView.THRESHOLD_RATIO
	var travel: float = threshold * 1.2
	_pointer(cv, start, true)
	await _frames(1)
	for i in range(1, 9):
		_pointer_move(cv, start + Vector2(travel * i / 8.0, 0))
		await _frames(1)
	ok(is_equal_approx(cv._offset, travel), "drag offset tracks the pointer (%.0f, expected %.0f)" % [cv._offset, travel])
	_pointer(cv, start + Vector2(travel, 0), false)
	await _settle(1.0)
	ok(GameState.watch == before_watch + 1, "drag past threshold committed the decision")
	Settings.data["reduced_motion"] = true
	Settings.changed.emit()

	# 4. Screens reachable during a run.
	for s in ["pause", "settings", "history", "objectives", "gallery", "archive", "endings"]:
		main._show_screen(s)
		await _frames(2)
		ok(main._current_screen == s and main._any_screen_visible(), "screen %s opens" % s)
	main._close_screens()
	await _frames(1)
	ok(not main._any_screen_visible(), "screens close back to play")
	# Escape backs out one level (regression: from a title sub-screen it left a blank view).
	main._show_screen("settings")
	await _frames(1)
	_escape()
	await _frames(2)
	ok(main._current_screen == "pause", "Escape from in-run settings returns to pause (got '%s')" % main._current_screen)
	_escape()
	await _frames(2)
	ok(not main._any_screen_visible(), "Escape from pause resumes play")

	# 5. Text scale + high contrast applied live.
	Settings.set_value("text_scale", 1.6)
	Settings.set_value("high_contrast", true)
	await _frames(2)
	ok(main.theme.default_font_size == int(UITheme.BASE_FONT * 1.6), "theme rebuilt at text scale 1.6")
	Settings.set_value("text_scale", 1.0)
	Settings.set_value("high_contrast", false)
	await _frames(1)

	# 6. Play 10 watches, save (autosave path), return to title, continue.
	await _play(10)
	var snap: Dictionary = GameState.snapshot()
	var mid_card: String = main.turn.current_card_id
	ok(SaveManager.save(slot), "manual save to slot %d" % slot)
	main._show_screen("title")
	await _frames(2)
	ok(not main.game_layer.visible, "title hides the game layer")
	main._show_screen("settings")
	await _frames(1)
	_escape()
	await _frames(2)
	ok(main._current_screen == "title", "Escape from title settings returns to the title (got '%s')" % main._current_screen)
	GameState.reset_profile()
	ok(SaveManager.load(slot), "load slot %d" % slot)
	main.continue_run()
	await _frames(3)
	ok(GameState.run["resources"] == snap["run"]["resources"], "resources restored after continue")
	ok(GameState.watch == snap["run"]["watch"], "watch restored after continue")
	ok(main.turn.current_card_id == mid_card, "same card shown after continue (%s)" % mid_card)
	ok(GameState.run["history"].size() == snap["run"]["history"].size(), "history restored")

	# 7. Play to an ending.
	var watched := await _play(max_watches)
	ok(endings_seen.size() == 1, "exactly one ending fired (got %d after %d watches)" % [endings_seen.size(), watched])
	ok(main._current_screen == "ending", "ending screen shown (got %s)" % main._current_screen)
	ok(not main.card_view.visible, "card hidden on ending screen")
	var ending_id: String = endings_seen[0] if endings_seen.size() > 0 else ""
	note("ending: %s at watch %d, run %d" % [ending_id, GameState.watch, GameState.run_number()])
	ok(GameState.profile["endings"].size() == 1, "ending recorded in Ledger")
	ok(not GameState.in_run(), "run is over")
	var ledger_unlocks: int = GameState.profile["unlocks"].size()

	# 8. Second Keeper: meta card, Ledger carries over.
	main.start_new_run(seed_value + 1)
	await _frames(3)
	ok(GameState.run_number() == 2, "run number 2")
	ok(GameState.profile["unlocks"].size() == ledger_unlocks, "unlocks persist into the next run")
	var seen: Array = [main.turn.current_card_id]
	main._request_decision("left")
	await _settle()
	seen.append(main.turn.current_card_id)
	ok(seen.has("onb_01") and seen.has("meta_new_keeper_2"), "second run opens with onb_01 and the meta card (%s)" % str(seen))
	await _play(5)
	ok(SaveManager.save(slot), "autosave-style save mid second run")
	main._show_screen("endings")
	await _frames(2)
	ok(main._current_screen == "endings", "ending history screen after a recorded ending")
	main._show_screen("credits")
	await _frames(2)
	ok(main._current_screen == "credits", "credits screen")

	# 9. Reload from disk one more time (fresh process would do this at boot).
	GameState.reset_profile()
	ok(SaveManager.load(slot), "reload slot after second run")
	ok(GameState.run_number() == 2 and GameState.in_run(), "second run resumes from disk")
	ok(GameState.profile["endings"].size() == 1, "Ledger ending history survives reload")

	note("subtitles emitted: %d; unlock notices: %d; fallbacks: %d" % [subtitles_seen, unlocks_seen, int(GameState.run["fallback_count"])])
	ok(int(GameState.run["fallback_count"]) == 0, "no fallback cards drawn")

	SaveManager.delete_slot(slot)
	Settings.data = saved_settings
	Settings.save_settings()
	_write_report(ending_id, watched)
	print("playtest: %d checks, %d failures" % [checks.size(), failures])
	get_tree().quit(1 if failures > 0 else 0)


## Plays up to n watches through the UI decision path using a simple keeper policy
## (nudge the most endangered resource). Returns watches played.
func _play(n: int) -> int:
	var played := 0
	while GameState.in_run() and played < n and main._current_screen != "ending":
		var card: Dictionary = main.card_view.card
		if card.is_empty():
			await _frames(2)
			if main.card_view.card.is_empty():
				break
			card = main.card_view.card
		var side := _policy(card)
		var h: int = GameState.run["history"].size()
		main._request_decision(side)
		await _until(func(): return not GameState.in_run() or GameState.run["history"].size() > h)
		played += 1
		if GameState.watch % 25 == 0:
			note("watch %d res=%s card=%s" % [GameState.watch, str(GameState.run["resources"]), main.turn.current_card_id])
	return played


func _policy(card: Dictionary) -> String:
	var best := "left"
	var best_score := -INF
	for side in ["left", "right"]:
		var res: Dictionary = card[side]["effects"].get("resources", {})
		var score := 0.0
		for r in main.RESOURCES:
			var v := GameState.get_resource(r)
			var d := int(res.get(r, 0))
			var after := v + d
			score -= abs(after - 50) - abs(v - 50)
			if r == "water":
				score += d * 1.5
		if score > best_score:
			best_score = score
			best = side
	return best


## Pointer events delivered straight to the card. `pos` is in the card holder's space (the card
## moves and rotates while dragged, so the local position is derived per event, as the viewport does).
func _pointer(cv: Control, pos: Vector2, pressed: bool) -> void:
	var ev := InputEventMouseButton.new()
	ev.button_index = MOUSE_BUTTON_LEFT
	ev.pressed = pressed
	ev.position = cv.get_transform().affine_inverse() * pos
	ev.global_position = cv.get_parent().get_global_transform() * pos
	cv._gui_input(ev)


func _pointer_move(cv: Control, pos: Vector2) -> void:
	var ev := InputEventMouseMotion.new()
	ev.position = cv.get_transform().affine_inverse() * pos
	ev.global_position = cv.get_parent().get_global_transform() * pos
	ev.button_mask = MOUSE_BUTTON_MASK_LEFT
	cv._gui_input(ev)


func _escape() -> void:
	var ev := InputEventKey.new()
	ev.keycode = KEY_ESCAPE
	ev.physical_keycode = KEY_ESCAPE
	ev.pressed = true
	main._unhandled_input(ev)


func _press_first_button() -> void:
	if main._screen_node == null:
		return
	for c in _walk(main._screen_node):
		if c is Button:
			c.pressed.emit()
			return


func _walk(node: Node) -> Array:
	var out := [node]
	for c in node.get_children():
		out += _walk(c)
	return out


func _write_report(ending_id: String, watched: int) -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://reports/validation"))
	var f := FileAccess.open("res://reports/validation/end_to_end_playtest.json", FileAccess.WRITE)
	f.store_string(JSON.stringify({
		"generated": Time.get_datetime_string_from_system(true),
		"seed": seed_value, "slot": slot, "godot": Engine.get_version_info()["string"],
		"checks": checks.size(), "failures": failures, "ending": ending_id, "watches_to_ending": watched,
		"subtitles": subtitles_seen, "unlock_notices": unlocks_seen,
		"log": log_lines, "results": checks,
	}, "\t"))
