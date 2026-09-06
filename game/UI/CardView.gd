class_name CardView
extends Control
## The draggable decision card. Handles mouse/touch drag with rotation, threshold, snap-back,
## commit animation, decision-label preview and resource-direction preview.
## Emits `decided(side)` when the player commits; Main applies the decision.

signal decided(side: String)
signal drag_progress(side: String, ratio: float)  # side "" when centered

const THRESHOLD_RATIO := 0.28   # of viewport width
const MAX_ROTATION_DEG := 12.0
const SNAP_TIME := 0.18
const COMMIT_TIME := 0.22
const RISE_TIME := 0.3

var card: Dictionary = {}
var _dragging := false
var _drag_start := Vector2.ZERO
var _origin := Vector2.ZERO
var _offset := 0.0
var _locked := false
var _tween: Tween

var panel: PanelContainer
var portrait: TextureRect
var name_label: Label
var role_label: Label
var text_label: RichTextLabel
var left_tab: Label
var right_tab: Label
var accent_bar: ColorRect
var placeholder_label: Label


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	focus_mode = Control.FOCUS_ALL
	_build()


func _build() -> void:
	panel = PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	var sb := UITheme.docket_box(UITheme.CHALK, UITheme.INK, 3, 26)
	sb.content_margin_left = 34
	sb.content_margin_right = 34
	sb.content_margin_top = 26
	sb.content_margin_bottom = 26
	sb.shadow_color = Color(0, 0, 0, 0.45)
	sb.shadow_size = 18
	sb.shadow_offset = Vector2(0, 10)
	panel.add_theme_stylebox_override("panel", sb)
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(panel)

	var v := VBoxContainer.new()
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_theme_constant_override("separation", 14)
	panel.add_child(v)

	var header := HBoxContainer.new()
	header.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(header)
	accent_bar = ColorRect.new()
	accent_bar.custom_minimum_size = Vector2(12, 64)
	accent_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	header.add_child(accent_bar)
	var names := VBoxContainer.new()
	names.mouse_filter = Control.MOUSE_FILTER_IGNORE
	names.add_theme_constant_override("separation", 0)
	names.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(names)
	name_label = Label.new()
	name_label.add_theme_color_override("font_color", UITheme.INK)
	name_label.add_theme_font_size_override("font_size", 36)
	names.add_child(name_label)
	role_label = Label.new()
	role_label.add_theme_color_override("font_color", UITheme.INK.lightened(0.35))
	role_label.add_theme_font_size_override("font_size", 24)
	names.add_child(role_label)

	var portrait_frame := CenterContainer.new()
	portrait_frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	portrait_frame.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(portrait_frame)
	portrait = TextureRect.new()
	portrait.mouse_filter = Control.MOUSE_FILTER_IGNORE
	portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	portrait.custom_minimum_size = Vector2(420, 520)
	portrait.size_flags_vertical = Control.SIZE_EXPAND_FILL
	portrait_frame.add_child(portrait)
	placeholder_label = Label.new()
	placeholder_label.text = ""
	placeholder_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	placeholder_label.add_theme_color_override("font_color", UITheme.INK.lightened(0.5))
	placeholder_label.add_theme_font_size_override("font_size", 20)
	placeholder_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(placeholder_label)

	text_label = RichTextLabel.new()
	text_label.bbcode_enabled = false
	text_label.fit_content = true
	text_label.scroll_active = false
	text_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	text_label.add_theme_color_override("default_color", UITheme.INK)
	text_label.add_theme_font_size_override("normal_font_size", 36)
	text_label.custom_minimum_size = Vector2(0, 200)
	text_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(text_label)

	var tabs := HBoxContainer.new()
	tabs.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(tabs)
	left_tab = _make_tab(HORIZONTAL_ALIGNMENT_LEFT)
	tabs.add_child(left_tab)
	right_tab = _make_tab(HORIZONTAL_ALIGNMENT_RIGHT)
	tabs.add_child(right_tab)
	pivot_offset = size / 2.0
	resized.connect(func(): pivot_offset = Vector2(size.x / 2.0, size.y))


func _make_tab(align: int) -> Label:
	var l := Label.new()
	l.horizontal_alignment = align
	l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	l.add_theme_color_override("font_color", UITheme.INK)
	l.add_theme_font_size_override("font_size", 28)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.modulate.a = 0.0
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func show_card(c: Dictionary, animate: bool = true) -> void:
	card = c
	_locked = false
	_offset = 0.0
	rotation = 0.0
	var ch := ContentDB.get_character(c["speaker"])
	name_label.text = str(ch.get("name", c["speaker"]))
	role_label.text = str(ch.get("role", ""))
	accent_bar.color = UITheme.faction_color(str(ch.get("faction", "none")))
	text_label.text = _resolve_text(c)
	left_tab.text = Loc.card_text(c, "left", c["left"]["label"])
	right_tab.text = Loc.card_text(c, "right", c["right"]["label"])
	left_tab.modulate.a = 0.0
	right_tab.modulate.a = 0.0
	_load_portrait(c)
	if animate and Settings.motion_scale() > 0.0:
		modulate.a = 0.0
		position.y = _origin.y + 80
		_kill_tween()
		_tween = create_tween().set_parallel(true)
		_tween.tween_property(self, "modulate:a", 1.0, RISE_TIME)
		_tween.tween_property(self, "position:y", _origin.y, RISE_TIME).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_CUBIC)
	else:
		modulate.a = 1.0
		position = _origin
	grab_focus()


func _resolve_text(c: Dictionary) -> String:
	var t: String = c["text"]
	for tv in c.get("text_variants", []):
		if Conditions.satisfied(tv["when"], GameState):
			t = tv["text"]
			break
	return Loc.card_text(c, "text", t)


func _load_portrait(c: Dictionary) -> void:
	var ch := ContentDB.get_character(c["speaker"])
	var expr: String = c.get("expression", "neutral")
	if not ch.get("expressions", []).has(expr):
		expr = str(ch.get("expressions", ["neutral"])[0])
	var path := "res://assets/portraits/%s_%s.png" % [ch.get("portrait_prefix", c["speaker"]), expr]
	if ResourceLoader.exists(path):
		portrait.texture = load(path)
		placeholder_label.text = ""
	else:
		portrait.texture = null
		placeholder_label.text = "[portrait missing: %s]" % path.get_file()


func set_origin(p: Vector2) -> void:
	_origin = p
	if not _dragging and not _locked:
		position = p


func _gui_input(event: InputEvent) -> void:
	if _locked:
		return
	if event is InputEventScreenTouch:
		if event.pressed:
			_begin_drag(event.position)
		else:
			_end_drag()
		accept_event()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_begin_drag(event.position)
		else:
			_end_drag()
		accept_event()
	elif (event is InputEventScreenDrag or event is InputEventMouseMotion) and _dragging:
		_update_drag(event.position)
		accept_event()


func _begin_drag(local_pos: Vector2) -> void:
	_dragging = true
	_drag_start = get_global_mouse_position()
	_kill_tween()
	AudioBus.play_sfx("sfx_card_drag")


func _update_drag(_local: Vector2) -> void:
	var dx := get_global_mouse_position().x - _drag_start.x
	_set_offset(dx)


func _set_offset(dx: float) -> void:
	_offset = dx
	var vw := get_viewport_rect().size.x
	var ratio: float = clamp(abs(dx) / (vw * THRESHOLD_RATIO), 0.0, 1.0)
	position.x = _origin.x + dx * (1.0 if Settings.motion_scale() > 0.0 else 0.35)
	rotation_degrees = (dx / max(vw, 1.0)) * MAX_ROTATION_DEG * 2.0 * Settings.motion_scale()
	var side := "left" if dx < 0 else "right"
	left_tab.modulate.a = ratio if dx < 0 else 0.0
	right_tab.modulate.a = ratio if dx > 0 else 0.0
	drag_progress.emit(side if ratio > 0.05 else "", ratio)


func _end_drag() -> void:
	if not _dragging:
		return
	_dragging = false
	var vw := get_viewport_rect().size.x
	if abs(_offset) >= vw * THRESHOLD_RATIO:
		commit("left" if _offset < 0 else "right")
	else:
		snap_back()


func snap_back() -> void:
	_kill_tween()
	var t := SNAP_TIME * (1.0 if Settings.motion_scale() > 0.0 else 0.4)
	_tween = create_tween().set_parallel(true)
	_tween.tween_property(self, "position", _origin, t).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_BACK)
	_tween.tween_property(self, "rotation_degrees", 0.0, t)
	_tween.tween_property(left_tab, "modulate:a", 0.0, t)
	_tween.tween_property(right_tab, "modulate:a", 0.0, t)
	_offset = 0.0
	drag_progress.emit("", 0.0)
	AudioBus.play_sfx("sfx_card_snap")


## Programmatic preview for keyboard/buttons: tilt toward a side without committing.
func preview_side(side: String) -> void:
	if _locked or _dragging:
		return
	var vw := get_viewport_rect().size.x
	var dx := vw * THRESHOLD_RATIO * 0.6 * (-1.0 if side == "left" else 1.0)
	_kill_tween()
	_tween = create_tween()
	_tween.tween_method(_set_offset, _offset, dx, 0.12 * max(Settings.motion_scale(), 0.3))


func clear_preview() -> void:
	if _locked or _dragging:
		return
	snap_back()


func commit(side: String) -> void:
	if _locked:
		return
	_locked = true
	_dragging = false
	AudioBus.play_sfx("sfx_card_commit")
	var vw := get_viewport_rect().size.x
	var target := _origin + Vector2((-1.0 if side == "left" else 1.0) * vw * 1.2, 40)
	_kill_tween()
	if Settings.motion_scale() > 0.0:
		_tween = create_tween().set_parallel(true)
		_tween.tween_property(self, "position", target, COMMIT_TIME).set_ease(Tween.EASE_IN).set_trans(Tween.TRANS_QUAD)
		_tween.tween_property(self, "rotation_degrees", (-1.0 if side == "left" else 1.0) * MAX_ROTATION_DEG * 1.5, COMMIT_TIME)
		_tween.tween_property(self, "modulate:a", 0.0, COMMIT_TIME)
		_tween.chain().tween_callback(func(): decided.emit(side))
	else:
		_tween = create_tween()
		_tween.tween_property(self, "modulate:a", 0.0, 0.12)
		_tween.tween_callback(func(): decided.emit(side))


func _kill_tween() -> void:
	if _tween != null and _tween.is_valid():
		_tween.kill()
