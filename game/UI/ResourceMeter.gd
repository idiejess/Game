class_name ResourceMeter
extends VBoxContainer
## One resource gauge: glyph + name, a bar with danger bands, preview arrows, and an exact readout
## when the accessibility option is on. Color is never the only signal: glyph shape and text
## arrows carry the same information.

var resource_id := ""
var bar: ProgressBar
var label: Label
var preview_label: Label
var value_label: Label
var _flash_tween: Tween


func setup(rid: String) -> void:
	resource_id = rid
	add_theme_constant_override("separation", 2)
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var top := HBoxContainer.new()
	add_child(top)
	label = Label.new()
	label.text = "%s %s" % [UITheme.RESOURCE_GLYPHS[rid], Loc.ui("res." + rid, rid.capitalize())]
	label.add_theme_font_size_override("font_size", UITheme.scaled(24))
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(label)
	preview_label = Label.new()
	preview_label.text = ""
	preview_label.add_theme_font_size_override("font_size", UITheme.scaled(26))
	preview_label.add_theme_color_override("font_color", UITheme.LAMP_AMBER)
	top.add_child(preview_label)
	bar = ProgressBar.new()
	bar.min_value = 0
	bar.max_value = 100
	bar.show_percentage = false
	bar.custom_minimum_size = Vector2(0, 22)
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0, 0, 0, 0.45)
	bg.set_corner_radius_all(6)
	bar.add_theme_stylebox_override("background", bg)
	var fill := StyleBoxFlat.new()
	fill.bg_color = UITheme.RESOURCE_COLORS[rid]
	fill.set_corner_radius_all(6)
	bar.add_theme_stylebox_override("fill", fill)
	add_child(bar)
	value_label = Label.new()
	value_label.add_theme_font_size_override("font_size", UITheme.scaled(20))
	value_label.visible = false
	add_child(value_label)
	tooltip_text = Loc.ui("res_desc." + rid, "")
	Settings.changed.connect(refresh_scale)


func refresh_scale() -> void:
	label.add_theme_font_size_override("font_size", UITheme.scaled(24))
	preview_label.add_theme_font_size_override("font_size", UITheme.scaled(26))
	value_label.add_theme_font_size_override("font_size", UITheme.scaled(20))


func set_value(v: int, animate: bool = true) -> void:
	if animate and Settings.motion_scale() > 0.0:
		var tw := create_tween()
		tw.tween_property(bar, "value", float(v), 0.35).set_ease(Tween.EASE_OUT)
	else:
		bar.value = v
	value_label.visible = bool(Settings.get_value("show_exact_effects"))
	value_label.text = str(v) + "/100"
	var danger := v <= 20 or v >= 80
	var warn := v <= 30 or v >= 70
	var fill: StyleBoxFlat = bar.get_theme_stylebox("fill")
	fill.border_color = UITheme.DANGER_RED if danger else Color(0, 0, 0, 0)
	fill.set_border_width_all(3 if danger else 0)
	var glyph: String = UITheme.RESOURCE_GLYPHS[resource_id]
	var mark := " !" if danger else (" ·" if warn else "")
	label.text = "%s %s%s" % [glyph, Loc.ui("res." + resource_id, resource_id.capitalize()), mark]


## delta: 0 hides; magnitude picks single or double arrow. Exact mode shows the number.
func set_preview(delta: int, ratio: float) -> void:
	if delta == 0 or ratio <= 0.05:
		preview_label.text = ""
		return
	var arrow := ("▲" if delta > 0 else "▼")
	if abs(delta) >= 8:
		arrow += arrow
	if Settings.get_value("show_exact_effects"):
		preview_label.text = "%s %+d" % [arrow, delta]
	else:
		preview_label.text = arrow
	preview_label.modulate.a = clamp(ratio + 0.3, 0.0, 1.0)


func flash(delta: int) -> void:
	if delta == 0 or Settings.motion_scale() <= 0.0:
		return
	if _flash_tween != null and _flash_tween.is_valid():
		_flash_tween.kill()
	_flash_tween = create_tween()
	var c := UITheme.CHARTER_GREEN if delta > 0 else UITheme.DANGER_RED
	_flash_tween.tween_property(label, "modulate", c, 0.1)
	_flash_tween.tween_property(label, "modulate", Color.WHITE, 0.5)
