class_name AssetReview
extends PanelContainer
## Development-only asset review gallery. Reads assets/art_manifest.csv and assets/audio_manifest.csv
## and shows every entry with id, filename, status, dimensions and license, plus play/stop/loop
## controls and a volume slider for audio. Opened from the developer panel (Main.dev_tools_enabled()).

var main
var _player: AudioStreamPlayer
var _status: Label
var _loop := false
var _art: Array = []
var _audio: Array = []
var _list: VBoxContainer
var _filter: OptionButton
var _detail: Control


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0, 0, 0, 0.95)
	add_theme_stylebox_override("panel", sb)
	_player = AudioStreamPlayer.new()
	add_child(_player)
	_player.finished.connect(func(): if _loop and _player.stream: _player.play())
	_art = _read_csv("res://assets/art_manifest.csv")
	_audio = _read_csv("res://assets/audio_manifest.csv")
	_build()


static func _read_csv(path: String) -> Array:
	var out: Array = []
	if not FileAccess.file_exists(path):
		return out
	var f := FileAccess.open(path, FileAccess.READ)
	var header := f.get_csv_line()
	while not f.eof_reached():
		var row := f.get_csv_line()
		if row.size() < header.size() or row[0] == "":
			continue
		var d := {}
		for i in range(header.size()):
			d[header[i]] = row[i]
		out.append(d)
	return out


func _build() -> void:
	var v := VBoxContainer.new()
	add_child(v)
	var top := HBoxContainer.new()
	v.add_child(top)
	var title := Label.new()
	title.text = "ASSET REVIEW (development build) — %d art, %d audio" % [_art.size(), _audio.size()]
	title.add_theme_color_override("font_color", UITheme.LAMP_AMBER)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(title)
	_filter = OptionButton.new()
	for k in ["portrait", "icon", "background", "ui", "branding", "ending_illustration", "app_icon", "music", "sfx"]:
		_filter.add_item(k)
	_filter.item_selected.connect(func(_i): _refresh())
	top.add_child(_filter)
	var close := Button.new()
	close.text = "Close"
	close.pressed.connect(func(): queue_free())
	top.add_child(close)
	var vol := HBoxContainer.new()
	v.add_child(vol)
	var vl := Label.new()
	vl.text = "Preview volume"
	vol.add_child(vl)
	var s := HSlider.new()
	s.min_value = 0
	s.max_value = 1
	s.step = 0.05
	s.value = 0.6
	s.custom_minimum_size = Vector2(300, 40)
	s.value_changed.connect(func(x): _player.volume_db = linear_to_db(max(x, 0.0001)))
	vol.add_child(s)
	var loop := CheckButton.new()
	loop.text = "Loop preview"
	loop.toggled.connect(func(on): _loop = on)
	vol.add_child(loop)
	var stop := Button.new()
	stop.text = "Stop"
	stop.pressed.connect(func(): _player.stop())
	vol.add_child(stop)
	_status = Label.new()
	_status.text = "Statuses come from the manifests. Tooling never sets approved_by_user; edit the CSV after human review."
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_status.theme_type_variation = "SmallLabel"
	v.add_child(_status)
	var h := HBoxContainer.new()
	h.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(h)
	var scroll := ScrollContainer.new()
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.size_flags_stretch_ratio = 1.2
	h.add_child(scroll)
	_list = VBoxContainer.new()
	_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(_list)
	_detail = VBoxContainer.new()
	_detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_detail.custom_minimum_size = Vector2(420, 0)
	h.add_child(_detail)
	_refresh()


func _refresh() -> void:
	for c in _list.get_children():
		c.queue_free()
	var kind: String = _filter.get_item_text(_filter.selected)
	var rows: Array = _audio if kind in ["music", "sfx"] else _art
	for r in rows:
		var t: String = r.get("asset_type", r.get("type", ""))
		if t != kind:
			continue
		var b := Button.new()
		var fn: String = r.get("final_filename", r.get("filename", ""))
		b.text = "%s  ·  %s  ·  %s / %s" % [r["asset_id"], fn, r.get("placeholder_status", ""), r.get("user_approval_status", "")]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.add_theme_font_size_override("font_size", 20)
		b.pressed.connect(func(): _show(r, kind))
		_list.add_child(b)


func _show(r: Dictionary, kind: String) -> void:
	for c in _detail.get_children():
		c.queue_free()
	var fn: String = r.get("final_filename", r.get("filename", ""))
	var dest: String = r.get("destination_path", r.get("destination", ""))
	var path := "res://" + dest + fn
	var info := RichTextLabel.new()
	info.fit_content = true
	info.add_theme_font_size_override("normal_font_size", 20)
	var lines := ["[b]%s[/b]" % r["asset_id"], "file: %s%s" % [dest, fn], "status: %s · approval: %s · integration: %s" % [r.get("placeholder_status", ""), r.get("user_approval_status", ""), r.get("integration_status", "")],
		"license: %s%s" % [r.get("license", ""), (" · source: " + r["source_url"]) if r.get("source_url", "") != "" else " (no external source)"],
		"purpose: %s" % r.get("narrative_purpose", "")]
	if kind in ["music", "sfx"]:
		lines.append("duration target %ss · loop %s · %s · %s Hz · %s ch" % [r.get("duration_target_s", ""), r.get("loop_required", ""), r.get("format", ""), r.get("sample_rate", ""), r.get("channels", "")])
	else:
		lines.append("%sx%s · %s · alpha %s · %s / %s" % [r.get("width", ""), r.get("height", ""), r.get("aspect_ratio", ""), r.get("alpha_required", ""), r.get("character_id", "-"), r.get("expression", "-")])
	if not ResourceLoader.exists(path):
		lines.append("[color=#C8352E]FILE MISSING[/color]")
	info.text = "\n".join(lines)
	_detail.add_child(info)
	if kind in ["music", "sfx"]:
		var play := Button.new()
		play.text = "Play"
		play.pressed.connect(func():
			if ResourceLoader.exists(path):
				_player.stream = load(path)
				_player.play())
		_detail.add_child(play)
	elif ResourceLoader.exists(path):
		var tex := TextureRect.new()
		tex.texture = load(path)
		tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		tex.custom_minimum_size = Vector2(400, 500)
		tex.size_flags_vertical = Control.SIZE_EXPAND_FILL
		_detail.add_child(tex)
