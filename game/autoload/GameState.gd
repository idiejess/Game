extends Node
## Holds the current run state and the cross-run profile, and applies card effects.
## Three scopes: turn (transient signals), run (`run` dict), persistent (`profile` dict).

signal resources_changed(deltas: Dictionary)
signal run_started(seed_value: int)
signal run_ended(ending_id: String)
signal watch_advanced(watch: int)
signal message(text: String)
signal unlock_gained(unlock_id: String)

const RESOURCES := ["water", "traffic", "coffers", "company", "town"]
const FACTIONS := ["company", "town", "hullfolk", "aldmere", "sorrel", "concordance"]
const START_RESOURCE := 50
const WATER_DRIFT := -1          # per watch; the mystery in mechanical form
const TRAFFIC_QUIET := 35        # traffic at or below: pound recovers +1 per watch
const TRAFFIC_BUSY := 70         # traffic at or above: pound loses an extra -1 per watch
const LEDGER_DAY_INTERVAL := 20
const LONG_WATCH := 100

var profile: Dictionary = {}
var run: Dictionary = {}
var watch: int:
	get:
		return int(run.get("watch", 0))
var rng: Rng = Rng.new(1)
var ended: bool = false
var last_fallback_unexpected := false


func _ready() -> void:
	reset_profile()


# ------------------------------------------------------------------ profile
func reset_profile() -> void:
	profile = {
		"run_number": 0,
		"unlocks": [], "lore": [], "objectives": [], "endings": [],
		"discovered_cards": [], "discovered_characters": [],
		"persistent_counters": {}, "persistent_flags": [], "achievements": [],
		"total_watches": 0,
	}
	run = {}
	ended = false


func run_number() -> int:
	return int(profile.get("run_number", 1))


func has_unlock(u: String) -> bool:
	return profile["unlocks"].has(u)


func has_ending(e: String) -> bool:
	for rec in profile["endings"]:
		if rec["id"] == e:
			return true
	return false


# ------------------------------------------------------------------ run lifecycle
func start_run(seed_value: int = -1) -> void:
	if seed_value < 0:
		seed_value = int(Time.get_unix_time_from_system()) ^ (randi() & 0x7FFFFFFF)
	profile["run_number"] = int(profile.get("run_number", 0)) + 1
	rng = Rng.new(seed_value)
	var resources := {}
	for r in RESOURCES:
		resources[r] = START_RESOURCE
	var rels := {}
	for cid in ContentDB.characters:
		var ch: Dictionary = ContentDB.characters[cid]
		if ch["tier"] != "source":
			rels[cid] = int(ch.get("initial_relationship", 50))
	var facs := {}
	for f in FACTIONS:
		facs[f] = 50
	var ctrs := {}
	for c in ContentDB.counters:
		if ContentDB.counters[c].get("scope", "run") == "run":
			ctrs[c] = int(ContentDB.counters[c].get("default", 0))
	run = {
		"seed": seed_value, "watch": 0, "resources": resources, "relationships": rels, "factions": facs,
		"flags": [], "counters": ctrs, "arcs": {}, "history": [], "cooldowns": {}, "appearances": {},
		"delayed": [], "delayed_resources": [], "forced_queue": [], "subdecks": [], "rng_state": rng.state,
		"current_card": null, "fallback_count": 0, "ended": null, "pending_ending": "",
	}
	ended = false
	_apply_persistent_openers()
	run_started.emit(seed_value)


## Cross-run state that modifies a fresh run (documented in FLAG_REGISTRY as persistent flags).
func _apply_persistent_openers() -> void:
	if profile["persistent_flags"].has("p_protected_quenn"):
		run["relationships"]["quenn"] = min(100, int(run["relationships"].get("quenn", 50)) + 10)
	if profile["persistent_flags"].has("p_honored_remembered"):
		run["factions"]["hullfolk"] = min(100, int(run["factions"]["hullfolk"]) + 8)


func end_run(ending_id: String) -> void:
	if ended:
		return
	ended = true
	run["ended"] = ending_id
	profile["endings"].append({"id": ending_id, "run": run_number(), "watch": watch})
	var ending: Dictionary = ContentDB.endings.get(ending_id, {})
	for u in ending.get("unlocks", []):
		grant_unlock(u)
	for l in ending.get("lore", []):
		if not profile["lore"].has(l):
			profile["lore"].append(l)
	_record_persistent_from_ending(ending_id)
	run_ended.emit(ending_id)


func _record_persistent_from_ending(ending_id: String) -> void:
	var pf: Array = profile["persistent_flags"]
	match ending_id:
		"end_res_water_min", "end_res_water_max":
			if not pf.has("p_prev_keeper_died_water"):
				pf.append("p_prev_keeper_died_water")
		"end_res_town_min":
			if not pf.has("p_prev_keeper_run_out"):
				pf.append("p_prev_keeper_run_out")
		"end_res_company_min":
			if not pf.has("p_prev_keeper_dismissed"):
				pf.append("p_prev_keeper_dismissed")
	if ending_id.begins_with("end_true_") and not pf.has("p_true_ending_seen"):
		pf.append("p_true_ending_seen")
	var kind: String = ContentDB.endings.get(ending_id, {}).get("kind", "")
	if kind == "resource_death" or kind == "crisis":
		add_persistent_counter("p_keepers_lost", 1)
	if has_flag("honored_remembered") and not pf.has("p_honored_remembered"):
		pf.append("p_honored_remembered")
	if has_flag("quenn_brave") and not pf.has("p_protected_quenn"):
		pf.append("p_protected_quenn")
	if has_flag("wren_jailed") and not pf.has("p_jailed_wren"):
		pf.append("p_jailed_wren")
	elif pf.has("p_jailed_wren") and not has_flag("wren_jailed"):
		pf.erase("p_jailed_wren")
	if has_flag("hullfolk_cleared") and not pf.has("p_clearance_done"):
		pf.append("p_clearance_done")
	if has_flag("told_mirren") and not pf.has("p_told_mirren"):
		pf.append("p_told_mirren")
	var cp := get_counter("cipher_progress")
	if cp > int(profile["persistent_counters"].get("p_cipher_progress", 0)):
		profile["persistent_counters"]["p_cipher_progress"] = cp


func in_run() -> bool:
	return not run.is_empty() and not ended


# ------------------------------------------------------------------ accessors
func get_resource(r: String) -> int:
	return int(run.get("resources", {}).get(r, START_RESOURCE))


func get_relationship(c: String) -> int:
	return int(run.get("relationships", {}).get(c, 50))


func get_faction(f: String) -> int:
	return int(run.get("factions", {}).get(f, 50))


func get_counter(c: String) -> int:
	if c.begins_with("p_"):
		return int(profile["persistent_counters"].get(c, 0))
	return int(run.get("counters", {}).get(c, 0))


func has_flag(f: String) -> bool:
	if f.begins_with("p_"):
		return profile["persistent_flags"].has(f)
	return run.get("flags", []).has(f)


func has_seen(cid: String) -> bool:
	return run.get("appearances", {}).has(cid)


func arc_stage(a: String) -> int:
	return int(run.get("arcs", {}).get(a, {}).get("stage", 0))


func arc_status(a: String) -> String:
	return str(run.get("arcs", {}).get(a, {}).get("status", "inactive"))


func add_persistent_counter(c: String, delta: int) -> void:
	profile["persistent_counters"][c] = int(profile["persistent_counters"].get(c, 0)) + delta


# ------------------------------------------------------------------ mutation
func set_resource(r: String, value: int) -> void:
	run["resources"][r] = clamp(value, 0, 100)


func set_flag(f: String, on: bool = true) -> void:
	if f.begins_with("p_"):
		var pf: Array = profile["persistent_flags"]
		if on and not pf.has(f):
			pf.append(f)
		elif not on:
			pf.erase(f)
		return
	var fl: Array = run["flags"]
	if on and not fl.has(f):
		fl.append(f)
	elif not on:
		fl.erase(f)


func set_counter(c: String, value: int) -> void:
	var reg: Dictionary = ContentDB.counters.get(c, {})
	var v := value
	if reg.has("min"):
		v = max(v, int(reg["min"]))
	if reg.has("max"):
		v = min(v, int(reg["max"]))
	if c.begins_with("p_"):
		profile["persistent_counters"][c] = v
	else:
		run["counters"][c] = v


func set_arc(a: String, stage: int = -1, status: String = "") -> void:
	if not run["arcs"].has(a):
		run["arcs"][a] = {"stage": 0, "status": "inactive"}
	if stage >= 0:
		run["arcs"][a]["stage"] = stage
	if status != "":
		run["arcs"][a]["status"] = status


func grant_unlock(u: String) -> void:
	if not profile["unlocks"].has(u):
		profile["unlocks"].append(u)
		unlock_gained.emit(u)


## Applies one choice's effects. Returns a dictionary describing what changed (for UI/tests).
func apply_effects(eff: Dictionary, card_id: String) -> Dictionary:
	var report := {"resources": {}, "ending": "", "messages": []}
	var deltas: Dictionary = eff.get("resources", {})
	for r in deltas:
		var before := get_resource(r)
		set_resource(r, before + int(deltas[r]))
		report["resources"][r] = get_resource(r) - before
	for c in eff.get("relationships", {}):
		run["relationships"][c] = clamp(get_relationship(c) + int(eff["relationships"][c]), 0, 100)
	for f in eff.get("factions", {}):
		run["factions"][f] = clamp(get_faction(f) + int(eff["factions"][f]), 0, 100)
	for f in eff.get("flags_set", []):
		set_flag(f, true)
	for f in eff.get("flags_clear", []):
		set_flag(f, false)
	for c in eff.get("counters", {}):
		set_counter(c, get_counter(c) + int(eff["counters"][c]))
	for c in eff.get("counters_set", {}):
		set_counter(c, int(eff["counters_set"][c]))
	if eff.has("followup"):
		run["forced_queue"].push_front(eff["followup"])
	for d in eff.get("delayed", []):
		var delay := int(d["delay"])
		if d.has("delay_max"):
			delay = rng.next_int(delay, int(d["delay_max"]))
		run["delayed"].append({"card": d["card"], "due": watch + delay})
	for dr in eff.get("delayed_resources", []):
		run["delayed_resources"].append({"due": watch + int(dr["delay"]), "resources": dr["resources"], "message": dr.get("message", "")})
	if eff.has("subdeck"):
		var sd: Dictionary = eff["subdeck"]
		var list: Array = sd["cards"].duplicate()
		if sd.get("shuffle", false):
			_shuffle(list)
		run["subdecks"].append({"id": sd["id"], "cards": list, "interleave": int(sd.get("interleave", 0)), "since": 0})
	for a in eff.get("arc", {}):
		var ad: Dictionary = eff["arc"][a]
		set_arc(a, int(ad.get("stage", -1)), str(ad.get("status", "")))
	for u in eff.get("unlocks", []):
		grant_unlock(u)
	for l in eff.get("lore", []):
		if not profile["lore"].has(l):
			profile["lore"].append(l)
	for o in eff.get("objectives_complete", []):
		if not profile["objectives"].has(o):
			profile["objectives"].append(o)
	if eff.has("ending"):
		var fire := true
		if eff.has("ending_chance"):
			fire = rng.next_float() < float(eff["ending_chance"])
		if fire:
			report["ending"] = eff["ending"]
	resources_changed.emit(report["resources"])
	return report


func _shuffle(list: Array) -> void:
	for i in range(list.size() - 1, 0, -1):
		var j := rng.next_int(0, i)
		var tmp = list[i]
		list[i] = list[j]
		list[j] = tmp


## Called after a decision is resolved. Advances the watch, applies drift and due delayed effects,
## then checks resource edges. Returns an ending id or "".
func advance_watch() -> String:
	run["watch"] = watch + 1
	profile["total_watches"] = int(profile.get("total_watches", 0)) + 1
	# Water drift. The pound also answers to traffic: a quiet gate lets the pound recover a mark,
	# a busy one spends an extra mark (the bible's "opening the gate spends Water for Traffic").
	var drift := WATER_DRIFT + get_counter("water_drift_mod")
	if has_flag("gates_leaking"):
		drift -= 1
	if has_flag("wet_season"):
		drift += 1
	if get_resource("traffic") <= TRAFFIC_QUIET:
		drift += 1
	elif get_resource("traffic") >= TRAFFIC_BUSY:
		drift -= 1
	if has_flag("sluice_rebuilt"):
		drift = 0
	set_resource("water", get_resource("water") + drift)
	# Cooldown tick
	var cds: Dictionary = run["cooldowns"]
	for cid in cds.keys():
		cds[cid] = int(cds[cid]) - 1
		if int(cds[cid]) <= 0:
			cds.erase(cid)
	# Delayed resources
	var remaining := []
	var agg := {}
	for dr in run["delayed_resources"]:
		if int(dr["due"]) <= watch:
			for r in dr["resources"]:
				set_resource(r, get_resource(r) + int(dr["resources"][r]))
				agg[r] = int(agg.get(r, 0)) + int(dr["resources"][r])
			if str(dr.get("message", "")) != "":
				message.emit(dr["message"])
		else:
			remaining.append(dr)
	run["delayed_resources"] = remaining
	if not agg.is_empty():
		resources_changed.emit(agg)
	run["rng_state"] = rng.state
	watch_advanced.emit(watch)
	return check_edges()


## Resource edge endings and the long-watch success.
func check_edges() -> String:
	for r in RESOURCES:
		var v := get_resource(r)
		if v <= 0:
			return _edge_ending(r, "min")
		if v >= 100:
			return _edge_ending(r, "max")
	return ""


## A resource edge fires the first ending (in endings.json order) whose trigger names that edge and
## whose conditions hold; the plain `end_res_<r>_<edge>` (no conditions) is the fallback.
func _edge_ending(r: String, edge: String) -> String:
	var fallback := "end_res_%s_%s" % [r, edge]
	for eid in ContentDB.endings:
		var trig: Dictionary = ContentDB.endings[eid].get("trigger", {})
		var re: Dictionary = trig.get("resource_edge", {})
		if re.get("resource", "") != r or re.get("edge", "") != edge:
			continue
		if trig.has("conditions"):
			if Conditions.satisfied(trig["conditions"], self):
				return eid
		elif eid != fallback:
			fallback = eid
	return fallback


## Data-driven non-edge endings (false endings, crisis endings): first satisfied wins.
func check_triggered_endings() -> String:
	for eid in ContentDB.endings:
		var trig: Dictionary = ContentDB.endings[eid].get("trigger", {})
		if trig.is_empty() or trig.has("resource_edge") or trig.get("long_watch", false):
			continue
		if not trig.has("conditions"):
			continue
		if trig.has("watch_min") and watch < int(trig["watch_min"]):
			continue
		if Conditions.satisfied(trig["conditions"], self):
			return eid
	return ""


## Watch-100 retirement: first `long_watch` candidate whose conditions hold, else the plain one.
func long_watch_ending() -> String:
	var fallback := ""
	for eid in ContentDB.endings:
		var trig: Dictionary = ContentDB.endings[eid].get("trigger", {})
		if trig.get("long_watch", false):
			if Conditions.satisfied(trig.get("conditions", {}), self):
				return eid
		elif trig.has("watch_min") and not trig.has("conditions") and not trig.has("resource_edge"):
			fallback = eid
	return fallback


func record_card_shown(cid: String) -> void:
	run["current_card"] = cid
	run["appearances"][cid] = int(run["appearances"].get(cid, 0)) + 1
	if not profile["discovered_cards"].has(cid):
		profile["discovered_cards"].append(cid)
	var spk: String = ContentDB.get_card(cid).get("speaker", "")
	if spk != "" and not spk.begins_with("src_") and not profile["discovered_characters"].has(spk):
		profile["discovered_characters"].append(spk)


func record_decision(cid: String, choice: String) -> void:
	run["history"].append({"card": cid, "watch": watch, "choice": choice})
	var card := ContentDB.get_card(cid)
	if card.has("cooldown") and int(card["cooldown"]) > 0:
		run["cooldowns"][cid] = int(card["cooldown"])
	run["current_card"] = null


func recent_history(n: int = 10) -> Array:
	var h: Array = run.get("history", [])
	return h.slice(max(0, h.size() - n), h.size())


func snapshot() -> Dictionary:
	return {"profile": profile.duplicate(true), "run": run.duplicate(true)}
