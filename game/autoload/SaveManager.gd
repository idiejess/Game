extends Node
## Versioned, atomic save system with migration and graceful recovery.
## Progression is saved to user://save_<slot>.json; settings live separately (Settings.gd).

signal saved(slot: int)
signal load_failed(reason: String)

const SAVE_VERSION := 2
const SLOT_COUNT := 3
const SAVE_DIR := "user://"

var current_slot := 1
var last_load_report := ""


func slot_path(slot: int) -> String:
	return SAVE_DIR + "save_%d.json" % slot


func backup_path(slot: int) -> String:
	return SAVE_DIR + "save_%d.bak.json" % slot


func slot_exists(slot: int) -> bool:
	return FileAccess.file_exists(slot_path(slot)) or FileAccess.file_exists(backup_path(slot))


## A saved run is resumable when it exists and has not ended; watch 0 (first card still showing)
## counts, otherwise quitting there loses the Keeper and inflates the run number.
static func _run_resumable(run) -> bool:
	return run is Dictionary and run.has("seed") and run.get("ended", null) == null


func slot_summary(slot: int) -> Dictionary:
	var data := _read(slot_path(slot))
	if data.is_empty():
		data = _read(backup_path(slot))
	if data.is_empty():
		return {}
	var prof: Dictionary = data.get("profile", {})
	var run = data.get("run", null)
	return {
		"run_number": int(prof.get("run_number", 0)),
		"endings": prof.get("endings", []).size(),
		"unlocks": prof.get("unlocks", []).size(),
		"in_run": _run_resumable(run),
		"watch": int(run.get("watch", 0)) if run is Dictionary else 0,
		"saved_at": str(data.get("saved_at", "")),
	}


func build_payload() -> Dictionary:
	var gs = GameState
	if not gs.run.is_empty():
		# Some RNG consumers (fallback pick, delay_max) do not write the state back themselves.
		gs.run["rng_state"] = gs.rng.state
	return {
		"save_version": SAVE_VERSION,
		"content_version": ContentDB.content_version,
		"saved_at": Time.get_datetime_string_from_system(true),
		"profile": gs.profile.duplicate(true),
		"run": gs.run.duplicate(true) if not gs.run.is_empty() else null,
	}


## Atomic write: write to .tmp, keep the previous file as .bak, then rename.
func save(slot: int = -1) -> bool:
	if slot < 0:
		slot = current_slot
	var path := slot_path(slot)
	var tmp := path + ".tmp"
	var payload := build_payload()
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		push_error("[SaveManager] cannot open %s for writing" % tmp)
		return false
	f.store_string(JSON.stringify(payload, "", false))
	f.close()
	var d := DirAccess.open(SAVE_DIR)
	if d == null:
		return false
	if FileAccess.file_exists(path):
		if FileAccess.file_exists(backup_path(slot)):
			d.remove(backup_path(slot))
		d.rename(path, backup_path(slot))
	var err := d.rename(tmp, path)
	if err != OK:
		push_error("[SaveManager] rename failed: %d" % err)
		return false
	saved.emit(slot)
	return true


func _read(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return {}
	var json := JSON.new()
	if json.parse(f.get_as_text()) != OK:
		return {}
	if not (json.data is Dictionary):
		return {}
	return _coerce_numbers(json.data)


## JSON parses every number as float; the sanitizers compare typeof() against int defaults, so
## whole-valued floats must become ints again or watch/seed/rng_state/run_number reset silently.
static func _coerce_numbers(v: Variant) -> Variant:
	match typeof(v):
		TYPE_FLOAT:
			return int(v) if is_equal_approx(v, floor(v)) else v
		TYPE_DICTIONARY:
			var out := {}
			for k in v:
				out[k] = _coerce_numbers(v[k])
			return out
		TYPE_ARRAY:
			var arr := []
			for item in v:
				arr.append(_coerce_numbers(item))
			return arr
		_:
			return v


## Loads a slot into GameState. Falls back to the backup, then to a fresh profile.
## Returns true if anything usable was loaded.
func load(slot: int = -1) -> bool:
	if slot < 0:
		slot = current_slot
	current_slot = slot
	var data := _read(slot_path(slot))
	var report := ""
	if not _valid(data):
		report = "primary save invalid; "
		data = _read(backup_path(slot))
		if not _valid(data):
			report += "backup invalid; starting fresh"
			last_load_report = report
			GameState.reset_profile()
			if FileAccess.file_exists(slot_path(slot)) or FileAccess.file_exists(backup_path(slot)):
				load_failed.emit(report)
			return false
		report += "recovered from backup"
	data = migrate(data)
	if data.is_empty():
		last_load_report = report + "; migration failed; starting fresh"
		GameState.reset_profile()
		load_failed.emit(last_load_report)
		return false
	GameState.profile = data["profile"]
	_ensure_profile_keys(GameState.profile)
	var run = data.get("run", null)
	if _run_resumable(run):
		GameState.run = _sanitize_run(run)
		GameState.rng = Rng.new(int(run.get("seed", 1)))
		GameState.rng.state = int(run.get("rng_state", GameState.rng.state))
		GameState.ended = false
	else:
		GameState.run = {}
		GameState.ended = false
	last_load_report = report if report != "" else "ok"
	return true


func _valid(data: Dictionary) -> bool:
	if data.is_empty():
		return false
	if not data.has("save_version") or not data.has("profile"):
		return false
	if not (data["profile"] is Dictionary):
		return false
	return true


## Migration chain. Each step converts version N to N+1. Unknown future versions are rejected.
func migrate(data: Dictionary) -> Dictionary:
	var v := int(data.get("save_version", 0))
	if v > SAVE_VERSION:
		push_warning("[SaveManager] save version %d newer than supported %d" % [v, SAVE_VERSION])
		return {}
	while v < SAVE_VERSION:
		match v:
			1:
				# v1 -> v2: persistent_counters/persistent_flags/total_watches added; endings as records.
				var p: Dictionary = data["profile"]
				p["persistent_counters"] = p.get("persistent_counters", {})
				p["persistent_flags"] = p.get("persistent_flags", [])
				p["total_watches"] = p.get("total_watches", 0)
				var fixed := []
				for e in p.get("endings", []):
					if e is String:
						fixed.append({"id": e, "run": 0, "watch": 0})
					else:
						fixed.append(e)
				p["endings"] = fixed
			_:
				# Version 0 or unknown: keep the profile if it looks like one.
				pass
		v += 1
		data["save_version"] = v
	return data


func _ensure_profile_keys(p: Dictionary) -> void:
	var defaults := {"run_number": 0, "unlocks": [], "lore": [], "objectives": [], "endings": [],
		"discovered_cards": [], "discovered_characters": [], "persistent_counters": {}, "persistent_flags": [],
		"achievements": [], "total_watches": 0}
	for k in defaults:
		if not p.has(k) or typeof(p[k]) != typeof(defaults[k]):
			p[k] = defaults[k]
	# Content updates: drop references to cards/unlocks that no longer exist.
	var dc: Array = p["discovered_cards"]
	var kept: Array = []
	for cid in dc:
		if ContentDB.has_card(cid):
			kept.append(cid)
	p["discovered_cards"] = kept


## Repairs a run dict so content changes never crash a resumed run.
func _sanitize_run(run: Dictionary) -> Dictionary:
	var defaults := {"seed": 1, "watch": 0, "resources": {}, "relationships": {}, "factions": {}, "flags": [],
		"counters": {}, "arcs": {}, "history": [], "cooldowns": {}, "appearances": {}, "delayed": [],
		"delayed_resources": [], "forced_queue": [], "subdecks": [], "rng_state": 1, "current_card": null,
		"fallback_count": 0, "ended": null, "pending_ending": ""}
	for k in defaults:
		if not run.has(k) or (defaults[k] != null and typeof(run[k]) != typeof(defaults[k])):
			run[k] = defaults[k]
	for r in GameState.RESOURCES:
		if not run["resources"].has(r):
			run["resources"][r] = GameState.START_RESOURCE
	run["forced_queue"] = run["forced_queue"].filter(func(c): return ContentDB.has_card(c))
	run["delayed"] = run["delayed"].filter(func(d): return d is Dictionary and ContentDB.has_card(str(d.get("card", ""))))
	if run["current_card"] != null and not ContentDB.has_card(str(run["current_card"])):
		run["current_card"] = null
	for cid in run["cooldowns"].keys():
		if not ContentDB.has_card(cid):
			run["cooldowns"].erase(cid)
	return run


func delete_slot(slot: int) -> void:
	var d := DirAccess.open(SAVE_DIR)
	if d == null:
		return
	for p in [slot_path(slot), backup_path(slot), slot_path(slot) + ".tmp"]:
		if FileAccess.file_exists(p):
			d.remove(p)


func export_state_text() -> String:
	return JSON.stringify(build_payload(), "  ", false)
