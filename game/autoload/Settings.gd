extends Node
## Player settings, stored separately from progression at user://settings.json.
## All accessibility options live here and persist across runs and saves.

signal changed

const PATH := "user://settings.json"
const VERSION := 1

var data: Dictionary = {}

const DEFAULTS := {
	"version": VERSION,
	"text_scale": 1.0,            # 0.8 .. 1.6
	"high_contrast": false,
	"reduced_motion": false,
	"screen_shake": true,
	"music_volume": 0.7,
	"sfx_volume": 0.8,
	"show_exact_effects": false,
	"show_buttons": true,
	"confirm_decisions": false,
	"subtitles": true,
	"language": "en",
	"content_warnings_seen": false,
	"tutorial_seen": false,
}


func _ready() -> void:
	load_settings()


func get_value(key: String) -> Variant:
	return data.get(key, DEFAULTS.get(key))


func set_value(key: String, value: Variant) -> void:
	if not DEFAULTS.has(key):
		push_warning("[Settings] unknown key %s" % key)
		return
	data[key] = value
	save_settings()
	changed.emit()


func load_settings() -> void:
	data = DEFAULTS.duplicate(true)
	if not FileAccess.file_exists(PATH):
		return
	var f := FileAccess.open(PATH, FileAccess.READ)
	if f == null:
		return
	var json := JSON.new()
	if json.parse(f.get_as_text()) != OK or not (json.data is Dictionary):
		push_warning("[Settings] invalid settings file; using defaults")
		return
	for k in json.data:
		if DEFAULTS.has(k) and typeof(json.data[k]) == typeof(DEFAULTS[k]):
			data[k] = json.data[k]
	data["version"] = VERSION
	changed.emit()


func save_settings() -> void:
	var f := FileAccess.open(PATH, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify(data, "  "))


func reset_defaults() -> void:
	data = DEFAULTS.duplicate(true)
	save_settings()
	changed.emit()


func motion_scale() -> float:
	return 0.0 if get_value("reduced_motion") else 1.0
