extends Node
## Plays placeholder cues and music. Assets are resolved from assets/audio/<id>.wav; missing
## assets are logged once and skipped so content never crashes on a missing cue.

signal subtitle(text: String)

var _players: Array[AudioStreamPlayer] = []
var _music: AudioStreamPlayer
var _current_music := ""
var _missing_reported: Dictionary = {}
var _sub_keys := {
	"sfx_telegram": "audio.telegram", "sfx_warning": "audio.warning", "sfx_death": "audio.death",
	"sfx_unlock": "audio.unlock", "mus_crisis": "audio.crisis_music",
}


func _ready() -> void:
	for i in range(6):
		var p := AudioStreamPlayer.new()
		add_child(p)
		_players.append(p)
	_music = AudioStreamPlayer.new()
	add_child(_music)
	Settings.changed.connect(_apply_volumes)
	_apply_volumes()


func _apply_volumes() -> void:
	var m := float(Settings.get_value("music_volume"))
	var s := float(Settings.get_value("sfx_volume"))
	_music.volume_db = linear_to_db(max(m, 0.0001))
	for p in _players:
		p.volume_db = linear_to_db(max(s, 0.0001))


func _load(id: String) -> AudioStream:
	var path := "res://assets/audio/%s.wav" % id
	if not ResourceLoader.exists(path):
		if not _missing_reported.has(id):
			_missing_reported[id] = true
			push_warning("[AudioBus] missing audio asset %s" % path)
		return null
	return load(path)


func play_sfx(id: String) -> void:
	if float(Settings.get_value("sfx_volume")) <= 0.0:
		_emit_subtitle(id)
		return
	var stream := _load(id)
	_emit_subtitle(id)
	if stream == null:
		return
	for p in _players:
		if not p.playing:
			p.stream = stream
			p.play()
			return
	_players[0].stream = stream
	_players[0].play()


func play_music(id: String) -> void:
	if id == _current_music:
		return
	_current_music = id
	_emit_subtitle(id)
	var stream := _load(id)
	if stream == null:
		_music.stop()
		return
	_music.stream = stream
	_music.play()


func stop_music() -> void:
	_current_music = ""
	_music.stop()


func _emit_subtitle(id: String) -> void:
	if Settings.get_value("subtitles") and _sub_keys.has(id):
		subtitle.emit(Loc.ui(_sub_keys[id].trim_prefix("ui."), ""))
