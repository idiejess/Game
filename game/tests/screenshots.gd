extends Node
## Visual regression harness. Runs the real Main scene, walks through representative states and
## saves PNGs to reports/screenshots/<size>/. Requires a display (xvfb-run is fine):
##   xvfb-run -s "-screen 0 1080x1920x24" godot --path . game/tests/Screenshots.tscn -- --size 540x960 --tag phone
## Optional: --text-scale 1.4 --contrast --exact --long-text --slot 3
## Uses save slot 3 (or --slot) and deletes it afterwards so player saves are untouched.

var main: Control
var out_dir := "res://reports/screenshots"
var tag := "default"
var slot := 3
var text_scale := 1.0
var high_contrast := false
var exact := false
var long_text := false


func _arg(name: String, default: String = "") -> String:
	var args := OS.get_cmdline_user_args()
	for i in range(args.size()):
		if args[i] == name and i + 1 < args.size() and not args[i + 1].begins_with("--"):
			return args[i + 1]
		if args[i] == name:
			return "true"
	return default


func _ready() -> void:
	tag = _arg("--tag", "default")
	slot = int(_arg("--slot", "3"))
	text_scale = float(_arg("--text-scale", "1.0"))
	high_contrast = _arg("--contrast") == "true"
	exact = _arg("--exact") == "true"
	long_text = _arg("--long-text") == "true"
	var size_s := _arg("--size", "540x960")
	var parts := size_s.split("x")
	get_window().size = Vector2i(int(parts[0]), int(parts[1]))
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out_dir + "/" + tag))
	# Isolated settings for this run (restored at the end).
	var saved_settings: Dictionary = Settings.data.duplicate(true)
	Settings.data["content_warnings_seen"] = true
	Settings.data["text_scale"] = text_scale
	Settings.data["high_contrast"] = high_contrast
	Settings.data["show_exact_effects"] = exact
	Settings.data["reduced_motion"] = true
	Settings.data["music_volume"] = 0.0
	Settings.data["sfx_volume"] = 0.0
	Settings.changed.emit()
	SaveManager.current_slot = slot
	SaveManager.delete_slot(slot)
	GameState.reset_profile()
	main = load("res://game/scripts/Main.gd").new()
	main.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(main)
	await _frames(4)
	await _shot("01_title")
	main.start_new_run(4242)
	await _frames(4)
	await _shot("02_first_card")
	if long_text:
		_show_longest_card()
		await _frames(3)
		await _shot("02b_longest_card")
	main.card_view.preview_side("right")
	await _frames(8)
	await _shot("03_preview_right")
	main.card_view.clear_preview()
	await _frames(8)
	for i in range(3):
		main.turn.decide("right")
		await _frames(2)
	await _shot("04_after_decisions")
	# Danger state
	GameState.set_resource("water", 12)
	GameState.set_resource("town", 88)
	main._refresh_hud()
	await _frames(3)
	await _shot("05_danger_meters")
	main._show_screen("pause")
	await _frames(3)
	await _shot("06_pause")
	main._show_screen("settings")
	await _frames(3)
	await _shot("07_settings")
	main._show_screen("history")
	await _frames(3)
	await _shot("08_history")
	main._show_screen("gallery")
	await _frames(3)
	await _shot("09_gallery")
	main._show_screen("slots", {"from": "pause"})
	await _frames(3)
	await _shot("10_slots")
	main._close_screens()
	# Ending
	GameState.set_resource("water", 1)
	GameState.run["forced_queue"].clear()
	main.turn.current_card_id = "onb_02"
	main.turn.decide("right")
	await _frames(3)
	await _shot("11_ending_card")
	main.turn.decide("left")
	await _frames(4)
	await _shot("12_ending_screen")
	if OS.has_feature("editor") or OS.is_debug_build():
		main.dev_panel.visible = true
		await _frames(3)
		await _shot("13_dev_panel")
		main.dev_panel.visible = false
	main._show_screen("credits")
	await _frames(3)
	await _shot("14_credits")
	SaveManager.delete_slot(slot)
	Settings.data = saved_settings
	Settings.save_settings()
	print("screenshots written to %s/%s" % [out_dir, tag])
	get_tree().quit(0)


func _show_longest_card() -> void:
	var best := ""
	var best_len := 0
	for cid in ContentDB.cards:
		var c: Dictionary = ContentDB.cards[cid]
		var l: int = c["text"].length() + c["left"]["label"].length() + c["right"]["label"].length()
		if l > best_len:
			best_len = l
			best = cid
	main.force_card(best)


func _frames(n: int) -> void:
	for i in range(n):
		await get_tree().process_frame


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(out_dir + "/%s/%s.png" % [tag, name])
