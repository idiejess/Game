class_name WaterLine
extends Control
## Background: the summit pound at night. The water line rises and falls with the Water resource.

var water_level := 50.0
var _target := 50.0
var _t := 0.0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)
	# With reduced motion there is no per-frame redraw, so a contrast toggle must trigger one.
	Settings.changed.connect(queue_redraw)


func set_water(v: int) -> void:
	_target = float(v)
	if Settings.motion_scale() <= 0.0:
		water_level = _target


func _process(delta: float) -> void:
	_t += delta
	if abs(water_level - _target) > 0.05:
		water_level = lerp(water_level, _target, min(1.0, delta * 2.5))
		queue_redraw()
	elif Settings.motion_scale() > 0.0:
		queue_redraw()


func _draw() -> void:
	var s := size
	var hc := bool(Settings.get_value("high_contrast"))
	var sky := Color.BLACK if hc else UITheme.POUND_GREEN.darkened(0.35)
	var water := Color("#0B2320") if hc else UITheme.POUND_GREEN
	draw_rect(Rect2(Vector2.ZERO, s), sky)
	# Water line sits between 82% (empty) and 38% (full) of the screen height.
	var y: float = lerp(s.y * 0.82, s.y * 0.38, water_level / 100.0)
	var pts := PackedVector2Array()
	var amp := 4.0 * Settings.motion_scale()
	var steps := 40
	for i in range(steps + 1):
		var x := s.x * float(i) / float(steps)
		pts.append(Vector2(x, y + sin(_t * 1.2 + float(i) * 0.5) * amp))
	pts.append(Vector2(s.x, s.y))
	pts.append(Vector2(0, s.y))
	draw_colored_polygon(pts, water)
	draw_polyline(pts.slice(0, steps + 1), UITheme.LAMP_AMBER.darkened(0.2) if not hc else Color.WHITE, 3.0, true)
	# Lamp reflection
	if not hc:
		var lx := s.x * 0.18
		draw_circle(Vector2(lx, y + 40), 60, Color(UITheme.LAMP_AMBER.r, UITheme.LAMP_AMBER.g, UITheme.LAMP_AMBER.b, 0.08))
		draw_circle(Vector2(lx, y + 40), 30, Color(UITheme.LAMP_AMBER.r, UITheme.LAMP_AMBER.g, UITheme.LAMP_AMBER.b, 0.10))
