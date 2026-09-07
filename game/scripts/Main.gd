extends Control
## Root controller: builds the UI tree, routes between screens, drives a TurnController.

const RESOURCES := ["water", "traffic", "coffers", "company", "town"]
const MAX_COLUMN_WIDTH := 720.0

var turn := TurnController.new()
var water_line: WaterLine
var column: Control
var screen_backdrop: ColorRect
var game_layer: Control
var hud: VBoxContainer
var meters: Dictionary = {}
var watch_label: Label
var run_label: Label
var card_holder: Control
var card_view: CardView
var left_btn: Button
var right_btn: Button
var buttons_row: HBoxContainer
var message_label: Label
var subtitle_label: Label
var screens: Control
var dev_panel: Control
var _pending_confirm := ""
var _shake_amount := 0.0
var _drag_armed := false
var _ended := false


func _ready() -> void:
	_apply_theme()
	Settings.changed.connect(_apply_theme)
	Settings.changed.connect(_on_settings_changed)
	_build()
	turn.card_drawn.connect(_on_card_drawn)
	turn.decision_applied.connect(_on_decision_applied)
	turn.ending_fired.connect(_on_ending)
	GameState.resources_changed.connect(_on_resources_changed)
	GameState.message.connect(_show_message)
	GameState.unlock_gained.connect(_on_unlock)
	CardSelector.fallback_used.connect(func(unexpected): if unexpected: _show_message(Loc.ui("fallback_notice", "A quiet watch.")))
	AudioBus.subtitle.connect(_show_subtitle)
	get_viewport().size_changed.connect(_layout)
	_layout()
	if not ContentDB.loaded:
		_show_screen("content_error")
		return
	if OS.get_cmdline_user_args().has("--smoke"):
		_smoke_test()
		return
	SaveManager.load(1)
	if not Settings.get_value("content_warnings_seen"):
		_show_screen("content_warning")
	else:
		_show_screen("title")


func _apply_theme() -> void:
	theme = UITheme.build(float(Settings.get_value("text_scale")), bool(Settings.get_value("high_contrast")))


func _on_settings_changed() -> void:
	if buttons_row:
		buttons_row.visible = bool(Settings.get_value("show_buttons"))
	for r in meters:
		meters[r].set_value(GameState.get_resource(r), false)
	_layout()


# ------------------------------------------------------------------ build
func _build() -> void:
	water_line = WaterLine.new()
	add_child(water_line)

	column = Control.new()
	column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(column)

	# Full-viewport dimmer behind menu screens; the column-bound screen sits on top of it so the
	# HUD never shows beside a menu on wide (desktop/landscape) viewports.
	screen_backdrop = ColorRect.new()
	screen_backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
	screen_backdrop.color = Color(0.06, 0.1, 0.1, 1.0)
	screen_backdrop.mouse_filter = Control.MOUSE_FILTER_STOP
	screen_backdrop.visible = false
	add_child(screen_backdrop)
	move_child(column, screen_backdrop.get_index())

	game_layer = Control.new()
	game_layer.set_anchors_preset(Control.PRESET_FULL_RECT)
	game_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(game_layer)

	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 28)
	game_layer.add_child(margin)
	var vbox := VBoxContainer.new()
	vbox.mouse_filter = Control.MOUSE_FILTER_IGNORE
	vbox.add_theme_constant_override("separation", 12)
	margin.add_child(vbox)

	# HUD top row: run/watch + pause
	var top := HBoxContainer.new()
	vbox.add_child(top)
	run_label = Label.new()
	run_label.theme_type_variation = "SmallLabel"
	top.add_child(run_label)
	watch_label = Label.new()
	watch_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	watch_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	top.add_child(watch_label)
	var pause_btn := Button.new()
	pause_btn.text = "≡"
	pause_btn.tooltip_text = Loc.ui("pause", "Pause")
	pause_btn.custom_minimum_size = Vector2(88, 88)
	pause_btn.pressed.connect(func(): _show_screen("pause"))
	top.add_child(pause_btn)

	hud = VBoxContainer.new()
	hud.add_theme_constant_override("separation", 6)
	vbox.add_child(hud)
	var meter_grid := GridContainer.new()
	meter_grid.columns = 5
	meter_grid.add_theme_constant_override("h_separation", 14)
	hud.add_child(meter_grid)
	for r in RESOURCES:
		var m := ResourceMeter.new()
		m.setup(r)
		meter_grid.add_child(m)
		meters[r] = m

	message_label = Label.new()
	message_label.theme_type_variation = "SmallLabel"
	message_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	message_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	message_label.custom_minimum_size = Vector2(0, 40)
	vbox.add_child(message_label)

	card_holder = Control.new()
	card_holder.size_flags_vertical = Control.SIZE_EXPAND_FILL
	card_holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	vbox.add_child(card_holder)
	card_view = CardView.new()
	card_view.decided.connect(_on_card_decided)
	card_view.drag_progress.connect(_on_drag_progress)
	card_view.visible = false
	card_holder.add_child(card_view)
	card_holder.resized.connect(_layout_card)

	buttons_row = HBoxContainer.new()
	buttons_row.add_theme_constant_override("separation", 20)
	vbox.add_child(buttons_row)
	left_btn = Button.new()
	left_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left_btn.custom_minimum_size = Vector2(0, 110)
	left_btn.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	left_btn.pressed.connect(func(): _request_decision("left"))
	left_btn.focus_entered.connect(func(): _preview("left"))
	left_btn.focus_exited.connect(_clear_preview)
	left_btn.mouse_entered.connect(func(): _preview("left"))
	left_btn.mouse_exited.connect(_clear_preview)
	buttons_row.add_child(left_btn)
	right_btn = Button.new()
	right_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right_btn.custom_minimum_size = Vector2(0, 110)
	right_btn.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	right_btn.pressed.connect(func(): _request_decision("right"))
	right_btn.focus_entered.connect(func(): _preview("right"))
	right_btn.focus_exited.connect(_clear_preview)
	right_btn.mouse_entered.connect(func(): _preview("right"))
	right_btn.mouse_exited.connect(_clear_preview)
	buttons_row.add_child(right_btn)
	buttons_row.visible = bool(Settings.get_value("show_buttons"))

	subtitle_label = Label.new()
	subtitle_label.theme_type_variation = "SmallLabel"
	subtitle_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle_label.custom_minimum_size = Vector2(0, 34)
	vbox.add_child(subtitle_label)

	screens = Control.new()
	screens.set_anchors_preset(Control.PRESET_FULL_RECT)
	screens.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(screens)

	dev_panel = load("res://game/UI/DevPanel.gd").new()
	dev_panel.main = self
	dev_panel.visible = false
	add_child(dev_panel)
	game_layer.visible = false


## Letterbox the play column on wide displays; full width on portrait phones.
func _layout() -> void:
	var vs := get_viewport_rect().size
	# Large text needs a wider column or the five-meter HUD overflows it in landscape.
	var max_w: float = MAX_COLUMN_WIDTH * max(1.0, float(Settings.get_value("text_scale")))
	var w: float = min(vs.x, max_w if vs.x > vs.y else vs.x)
	column.position = Vector2((vs.x - w) / 2.0, 0)
	column.size = Vector2(w, vs.y)
	_layout_card()


func _layout_card() -> void:
	if card_view == null or card_holder == null:
		return
	var hs := card_holder.size
	var cw: float = min(hs.x, 640.0)
	var chh: float = min(hs.y, 1500.0)
	card_view.size = Vector2(cw, chh)
	card_view.pivot_offset = Vector2(cw / 2.0, chh)
	card_view.set_origin(Vector2((hs.x - cw) / 2.0, (hs.y - chh) / 2.0))


## Developer tools ship disabled in release exports; debug builds, the editor and the
## `--dev` command-line flag enable them.
static func dev_tools_enabled() -> bool:
	return OS.is_debug_build() or OS.has_feature("editor") or OS.get_cmdline_user_args().has("--dev")


## `--smoke` (works in exported builds): plays 30 watches on a fixed seed into save slot 3, reloads,
## verifies the state round-trips, prints a summary and exits non-zero on any failure.
func _smoke_test() -> void:
	var failures := 0
	SaveManager.current_slot = 3
	SaveManager.delete_slot(3)
	GameState.reset_profile()
	turn.autosave = false
	turn.begin_run(4242)
	game_layer.visible = true
	var i := 0
	while GameState.in_run() and i < 30:
		turn.decide("left" if i % 2 == 0 else "right")
		i += 1
	print("smoke: cards=%d watch=%d resources=%s ended=%s fallbacks=%d" % [ContentDB.cards.size(), GameState.watch, str(GameState.run["resources"]), str(GameState.run.get("ended")), int(GameState.run["fallback_count"])])
	if GameState.in_run():
		var snap: Dictionary = GameState.snapshot()
		if not SaveManager.save(3):
			failures += 1
			printerr("smoke: save failed")
		GameState.reset_profile()
		if not SaveManager.load(3):
			failures += 1
			printerr("smoke: load failed")
		if GameState.run.get("resources") != snap["run"]["resources"] or GameState.run.get("watch") != snap["run"]["watch"]:
			failures += 1
			printerr("smoke: state did not round-trip")
		print("smoke: save/load round-trip %s" % ("ok" if failures == 0 else "FAILED"))
	if ContentDB.cards.size() != ContentDB.EXPECTED_TOTAL:
		failures += 1
	if Loc.strings.size() < 1000:
		failures += 1
		printerr("smoke: localization not loaded (%d strings)" % Loc.strings.size())
	SaveManager.delete_slot(3)
	get_tree().quit(1 if failures > 0 else 0)


# ------------------------------------------------------------------ input
func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_dev_panel"):
		if not dev_tools_enabled():
			return
		dev_panel.visible = not dev_panel.visible
		if dev_panel.visible:
			dev_panel.refresh()
		get_viewport().set_input_as_handled()
		return
	if not game_layer.visible or _ended or _any_screen_visible():
		if event.is_action_pressed("pause_menu") and _any_screen_visible():
			# Escape backs out one level, mirroring each screen's Back button.
			match _current_screen:
				"pause":
					_close_screens()
				"settings", "history", "objectives", "gallery", "archive":
					_show_screen("pause" if GameState.in_run() and game_layer.visible and not _ended else "title")
				"endings", "slots", "credits":
					_show_screen("title")
				_:
					return
			get_viewport().set_input_as_handled()
		return
	if event.is_action_pressed("pause_menu"):
		_show_screen("pause")
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("decide_left"):
		_preview("left")
	elif event.is_action_pressed("decide_right"):
		_preview("right")
	elif event.is_action_released("decide_left"):
		_request_decision("left")
	elif event.is_action_released("decide_right"):
		_request_decision("right")


func _preview(side: String) -> void:
	if card_view.visible and not _ended:
		card_view.preview_side(side)


func _clear_preview() -> void:
	if card_view.visible and not _ended:
		card_view.clear_preview()


func _on_drag_progress(side: String, ratio: float) -> void:
	if card_view.card.is_empty():
		return
	for r in RESOURCES:
		var d := 0
		if side != "":
			d = int(TurnController.preview(card_view.card, side).get(r, 0))
		meters[r].set_preview(d, ratio)
	# Cue once when the drag crosses the commit threshold, not on every motion event past it.
	var armed := ratio >= 1.0 and side != ""
	if armed and not _drag_armed:
		AudioBus.play_sfx("sfx_card_tilt")
	_drag_armed = armed


func _request_decision(side: String) -> void:
	if _ended or not card_view.visible or card_view.card.is_empty():
		return
	if Settings.get_value("confirm_decisions") and _pending_confirm != side:
		_pending_confirm = side
		var label: String = Loc.card_text(card_view.card, side, card_view.card[side]["label"])
		_show_message(Loc.ui("confirm_hint", "Choose again to confirm: ") + label)
		card_view.preview_side(side)
		return
	_pending_confirm = ""
	card_view.commit(side)


func _on_card_decided(side: String) -> void:
	turn.decide(side)


# ------------------------------------------------------------------ turn callbacks
func _on_card_drawn(cid: String) -> void:
	var card := ContentDB.get_card(cid)
	card_view.visible = true
	_layout_card()
	card_view.show_card(card)
	left_btn.text = "◄  " + Loc.card_text(card, "left", card["left"]["label"])
	right_btn.text = Loc.card_text(card, "right", card["right"]["label"]) + "  ►"
	_pending_confirm = ""
	_refresh_hud()
	if card.has("sound"):
		AudioBus.play_sfx(card["sound"])
	var danger := false
	for r in RESOURCES:
		var v := GameState.get_resource(r)
		if v <= 20 or v >= 80:
			danger = true
	AudioBus.play_music("mus_crisis" if danger else "mus_ambient")


func _on_decision_applied(cid: String, side: String, report: Dictionary) -> void:
	var card := ContentDB.get_card(cid)
	var outcome: String = card[side].get("outcome", "")
	if outcome != "":
		_show_message(Loc.card_text(card, side + "_outcome", outcome))
	else:
		message_label.text = ""
	for r in report.get("resources", {}):
		meters[r].flash(int(report["resources"][r]))
	var eff: Dictionary = card[side]["effects"]
	if eff.get("shake", false) and Settings.get_value("screen_shake") and Settings.motion_scale() > 0.0:
		_shake_amount = 14.0
	if eff.has("sound"):
		AudioBus.play_sfx(eff["sound"])
	for r in meters:
		meters[r].set_preview(0, 0.0)


func _on_resources_changed(deltas: Dictionary) -> void:
	_refresh_hud()
	var up := false
	var down := false
	for r in deltas:
		if int(deltas[r]) > 0:
			up = true
		elif int(deltas[r]) < 0:
			down = true
		var v := GameState.get_resource(r)
		if v <= 20 or v >= 80:
			AudioBus.play_sfx("sfx_warning")
	if up:
		AudioBus.play_sfx("sfx_res_up")
	if down:
		AudioBus.play_sfx("sfx_res_down")


func _refresh_hud() -> void:
	for r in RESOURCES:
		meters[r].set_value(GameState.get_resource(r))
	water_line.set_water(GameState.get_resource("water"))
	watch_label.text = Loc.ui("watch", "Watch") + " %d" % GameState.watch
	run_label.text = Loc.ui("keeper", "Keeper") + " %d" % GameState.run_number()


func _on_ending(ending_id: String) -> void:
	_ended = true
	card_view.visible = false
	var ending: Dictionary = ContentDB.endings.get(ending_id, {})
	AudioBus.play_sfx("sfx_death" if ending.get("kind", "") in ["resource_death", "crisis"] else "sfx_unlock")
	AudioBus.play_music(str(ending.get("music", "mus_ending_fail")))
	_show_screen("ending", {"ending": ending_id})


func _on_unlock(u: String) -> void:
	AudioBus.play_sfx("sfx_unlock")
	_show_message(Loc.ui("unlock_notice", "The Ledger records: ") + Loc.ui("unlock." + u, u.trim_prefix("unlock_").replace("_", " ")))


func _show_message(text: String) -> void:
	message_label.text = text


func _show_subtitle(text: String) -> void:
	subtitle_label.text = text
	var tw := create_tween()
	tw.tween_interval(2.5)
	tw.tween_callback(func(): if subtitle_label.text == text: subtitle_label.text = "")


func _process(delta: float) -> void:
	if _shake_amount > 0.0:
		game_layer.position = Vector2(randf_range(-1, 1), randf_range(-1, 1)) * _shake_amount
		_shake_amount = max(0.0, _shake_amount - delta * 60.0)
		if _shake_amount <= 0.0:
			game_layer.position = Vector2.ZERO


# ------------------------------------------------------------------ run control
func start_new_run(seed_value: int = -1) -> void:
	_ended = false
	_close_screens()
	game_layer.visible = true
	turn.begin_run(seed_value)
	_refresh_hud()


func continue_run() -> void:
	_ended = false
	_close_screens()
	game_layer.visible = true
	turn.resume_run()
	_refresh_hud()


## Dev panel hook: force a card immediately.
func force_card(cid: String) -> void:
	if not GameState.in_run():
		start_new_run()
	GameState.run["forced_queue"].push_front(cid)
	_ended = false
	turn.draw()


# ------------------------------------------------------------------ screens
var _current_screen := ""
var _screen_node: Control


func _any_screen_visible() -> bool:
	return _screen_node != null and is_instance_valid(_screen_node)


func _close_screens() -> void:
	if _screen_node != null and is_instance_valid(_screen_node):
		_screen_node.queue_free()
	_screen_node = null
	_current_screen = ""
	if screen_backdrop:
		screen_backdrop.visible = false
	if game_layer.visible and card_view.visible:
		card_view.grab_focus()


func _show_screen(name: String, args: Dictionary = {}) -> void:
	_close_screens()
	_current_screen = name
	var Screens = load("res://game/UI/Screens.gd")
	_screen_node = Screens.make(name, self, args)
	screens.add_child(_screen_node)
	screen_backdrop.visible = true
	if name == "title":
		game_layer.visible = false
		AudioBus.play_music("mus_title")
