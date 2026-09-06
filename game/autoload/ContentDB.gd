extends Node
## Loads and strictly validates all shipped content (cards, characters, endings, registries,
## story graph) and builds the indexes used by CardSelector.
##
## Card files: res://content/cards/<category>/*.json, each {"cards": [ {...}, ... ]}.
## Validation errors are collected in `errors`; loading fails loudly rather than skipping fields.

signal content_loaded(ok: bool)

const CARD_ROOT := "res://content/cards"
const CATEGORIES := ["onboarding", "evergreen", "resources", "relationships", "minor_arcs", "major_arcs", "crises", "endings_meta"]
const RESOURCES := ["water", "traffic", "coffers", "company", "town"]
const FACTIONS := ["company", "town", "hullfolk", "aldmere", "sorrel", "concordance"]
const POOLS := ["general", "character", "crisis", "forced", "ending", "fallback"]
const EXPECTED_TOTAL := 1000

var cards: Dictionary = {}            # id -> card dict
var characters: Dictionary = {}       # id -> character dict
var endings: Dictionary = {}          # id -> ending dict
var flags: Dictionary = {}            # id -> registry entry
var counters: Dictionary = {}         # id -> registry entry
var story_graph: Dictionary = {}
var inventory_ids: Dictionary = {}    # id -> inventory entry

# Indexes
var by_category: Dictionary = {}      # category -> Array[id]
var by_speaker: Dictionary = {}       # speaker -> Array[id]
var by_arc: Dictionary = {}           # arc id -> Array[id]
var by_pool: Dictionary = {}          # pool -> Array[id]
var by_resource_tag: Dictionary = {}  # resource -> Array[id] (cards tagged res:<name>)
var unconditional_general: Array = [] # general-pool cards with no conditions (fast path)
var conditional_general: Array = []   # general-pool cards with conditions
var fallback_cards: Array = []

var errors: PackedStringArray = []
var warnings: PackedStringArray = []
var loaded := false
var content_version := "0.0.0"
var strict_total := true              # set false in tests that load partial content


func _ready() -> void:
	load_all()


func load_all() -> bool:
	errors.clear()
	warnings.clear()
	cards.clear()
	characters.clear()
	endings.clear()
	flags.clear()
	counters.clear()
	for idx in [by_category, by_speaker, by_arc, by_pool, by_resource_tag]:
		idx.clear()
	unconditional_general.clear()
	conditional_general.clear()
	fallback_cards.clear()

	_load_registries()
	_load_characters()
	_load_endings()
	_load_story_graph()
	_load_inventory()
	_load_cards()
	_cross_validate()
	_build_indexes()

	loaded = errors.is_empty()
	if not loaded:
		for e in errors:
			push_error("[ContentDB] " + e)
	for w in warnings:
		push_warning("[ContentDB] " + w)
	content_version = ProjectSettings.get_setting("application/config/version", "0.0.0")
	content_loaded.emit(loaded)
	return loaded


func _read_json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		errors.append("missing file %s" % path)
		return null
	var f := FileAccess.open(path, FileAccess.READ)
	var text := f.get_as_text()
	var json := JSON.new()
	var err := json.parse(text)
	if err != OK:
		errors.append("%s: JSON parse error line %d: %s" % [path, json.get_error_line(), json.get_error_message()])
		return null
	return json.data


func _list_files(dir_path: String, ext: String) -> PackedStringArray:
	var out: PackedStringArray = []
	var d := DirAccess.open(dir_path)
	if d == null:
		return out
	d.list_dir_begin()
	var name := d.get_next()
	while name != "":
		if not d.current_is_dir() and name.ends_with(ext):
			out.append(dir_path.path_join(name))
		name = d.get_next()
	d.list_dir_end()
	out.sort()
	return out


func _load_registries() -> void:
	var fr = _read_json("res://content/FLAG_REGISTRY.json")
	if fr is Dictionary:
		for e in fr.get("flags", []):
			flags[e["id"]] = e
	var cr = _read_json("res://content/COUNTER_REGISTRY.json")
	if cr is Dictionary:
		for e in cr.get("counters", []):
			counters[e["id"]] = e


func _load_characters() -> void:
	for path in _list_files("res://content/characters", ".json"):
		var c = _read_json(path)
		if not (c is Dictionary):
			continue
		for req in ["id", "name", "role", "tier", "faction", "expressions", "portrait_prefix"]:
			if not c.has(req):
				errors.append("%s: character missing '%s'" % [path, req])
		if c.has("id"):
			characters[c["id"]] = c


func _load_endings() -> void:
	for path in _list_files("res://content/endings", ".json"):
		var data = _read_json(path)
		if data is Dictionary and data.has("endings"):
			for e in data["endings"]:
				if not (e is Dictionary) or not e.has("id"):
					errors.append("%s: ending without id" % path)
					continue
				for req in ["title", "kind", "card", "epilogue"]:
					if not e.has(req):
						errors.append("%s: ending %s missing '%s'" % [path, e["id"], req])
				endings[e["id"]] = e


func _load_story_graph() -> void:
	var g = _read_json("res://content/STORY_GRAPH.json")
	if g is Dictionary:
		story_graph = g


func _load_inventory() -> void:
	var inv = _read_json("res://content/CARD_INVENTORY.json")
	if inv is Dictionary:
		for e in inv.get("cards", []):
			inventory_ids[e["id"]] = e


func _load_cards() -> void:
	for cat in CATEGORIES:
		var dir_path := CARD_ROOT.path_join(cat)
		for path in _list_files(dir_path, ".json"):
			var data = _read_json(path)
			if not (data is Dictionary) or not data.has("cards") or not (data["cards"] is Array):
				errors.append("%s: expected {\"cards\": [...]}" % path)
				continue
			for card in data["cards"]:
				_validate_card(card, path, cat)


func _validate_card(card: Variant, path: String, dir_cat: String) -> void:
	if not (card is Dictionary):
		errors.append("%s: card is not an object" % path)
		return
	var cid: String = str(card.get("id", "<no id>"))
	var where := "%s [%s]" % [path.get_file(), cid]
	for req in ["id", "category", "speaker", "text", "left", "right"]:
		if not card.has(req):
			errors.append("%s: missing required field '%s'" % [where, req])
			return
	if cards.has(cid):
		errors.append("%s: duplicate card id" % where)
		return
	if card["category"] != dir_cat:
		errors.append("%s: category '%s' does not match directory '%s'" % [where, card["category"], dir_cat])
	if not CATEGORIES.has(card["category"]):
		errors.append("%s: unknown category '%s'" % [where, card["category"]])
	if not (card["text"] is String) or card["text"].strip_edges().is_empty():
		errors.append("%s: text must be a non-empty string" % where)
	var allowed := ["id", "category", "speaker", "expression", "text", "text_variants", "left", "right", "conditions",
		"weight", "weight_mods", "cooldown", "max_per_run", "pool", "arc", "tags", "sound", "achievement", "loc_key", "notes"]
	for k in card.keys():
		if not allowed.has(k):
			errors.append("%s: unknown field '%s'" % [where, k])
	if card.has("pool") and not POOLS.has(card["pool"]):
		errors.append("%s: unknown pool '%s'" % [where, card["pool"]])
	if card.has("weight") and (not (card["weight"] is float or card["weight"] is int) or float(card["weight"]) <= 0.0):
		errors.append("%s: weight must be > 0" % where)
	if card.has("arc"):
		var a = card["arc"]
		if not (a is Dictionary) or not a.has("id") or not a.has("stage"):
			errors.append("%s: arc must have id and stage" % where)
	for side in ["left", "right"]:
		var ch = card[side]
		if not (ch is Dictionary) or not ch.has("label") or not ch.has("effects"):
			errors.append("%s: %s choice needs label and effects" % [where, side])
			continue
		_validate_effects(ch["effects"], where + "." + side)
	if card.has("conditions"):
		_validate_conditions(card["conditions"], where + ".conditions")
	for wm in card.get("weight_mods", []):
		if wm is Dictionary and wm.has("when"):
			_validate_conditions(wm["when"], where + ".weight_mods")
	for tv in card.get("text_variants", []):
		if tv is Dictionary and tv.has("when"):
			_validate_conditions(tv["when"], where + ".text_variants")
	cards[cid] = card


func _validate_effects(eff: Variant, where: String) -> void:
	if not (eff is Dictionary):
		errors.append("%s: effects must be an object" % where)
		return
	var allowed := ["resources", "relationships", "factions", "flags_set", "flags_clear", "counters", "counters_set",
		"followup", "delayed", "delayed_resources", "subdeck", "arc", "unlocks", "lore", "objectives_complete",
		"ending", "ending_chance", "shake", "sound"]
	for k in eff.keys():
		if not allowed.has(k):
			errors.append("%s: unknown effect '%s'" % [where, k])
	for r in eff.get("resources", {}).keys():
		if not RESOURCES.has(r):
			errors.append("%s: unknown resource '%s'" % [where, r])
	for f in eff.get("factions", {}).keys():
		if not FACTIONS.has(f):
			errors.append("%s: unknown faction '%s'" % [where, f])
	for f in eff.get("flags_set", []) + eff.get("flags_clear", []):
		if not flags.has(f):
			errors.append("%s: undeclared flag '%s'" % [where, f])
	for c in eff.get("counters", {}).keys() + eff.get("counters_set", {}).keys():
		if not counters.has(c):
			errors.append("%s: undeclared counter '%s'" % [where, c])


func _validate_conditions(cond: Variant, where: String) -> void:
	if not (cond is Dictionary):
		errors.append("%s: conditions must be an object" % where)
		return
	var allowed := ["flags_all", "flags_any", "flags_none", "resources", "relationships", "factions", "counters", "run",
		"watch", "seen_cards", "unseen_cards", "seen_cards_any", "unlocks", "unlocks_none", "arc_stage", "arc_status",
		"endings_seen", "endings_unseen"]
	for k in cond.keys():
		if not allowed.has(k):
			errors.append("%s: unknown condition '%s'" % [where, k])
	for f in cond.get("flags_all", []) + cond.get("flags_any", []) + cond.get("flags_none", []):
		if not flags.has(f):
			errors.append("%s: undeclared flag '%s'" % [where, f])
	for c in cond.get("counters", {}).keys():
		if not counters.has(c):
			errors.append("%s: undeclared counter '%s'" % [where, c])
	for r in cond.get("resources", {}).keys():
		if not RESOURCES.has(r):
			errors.append("%s: unknown resource '%s'" % [where, r])


func _cross_validate() -> void:
	# References between cards, speakers, endings.
	for cid in cards:
		var card: Dictionary = cards[cid]
		if not characters.has(card["speaker"]):
			errors.append("[%s] unknown speaker '%s'" % [cid, card["speaker"]])
		elif card.has("expression") and not characters[card["speaker"]]["expressions"].has(card["expression"]):
			errors.append("[%s] speaker '%s' has no expression '%s'" % [cid, card["speaker"], card["expression"]])
		for side in ["left", "right"]:
			var eff: Dictionary = card[side]["effects"]
			if eff.has("followup") and not cards.has(eff["followup"]):
				errors.append("[%s] %s.followup references unknown card '%s'" % [cid, side, eff["followup"]])
			for d in eff.get("delayed", []):
				if not cards.has(d["card"]):
					errors.append("[%s] %s.delayed references unknown card '%s'" % [cid, side, d["card"]])
			if eff.has("subdeck"):
				for sc in eff["subdeck"]["cards"]:
					if not cards.has(sc):
						errors.append("[%s] %s.subdeck references unknown card '%s'" % [cid, side, sc])
			if eff.has("ending") and not endings.has(eff["ending"]):
				errors.append("[%s] %s.ending references unknown ending '%s'" % [cid, side, eff["ending"]])
		if card.has("conditions"):
			for k in ["seen_cards", "unseen_cards", "seen_cards_any"]:
				for ref in card["conditions"].get(k, []):
					if not cards.has(ref):
						errors.append("[%s] conditions.%s references unknown card '%s'" % [cid, k, ref])
	for eid in endings:
		if not cards.has(endings[eid]["card"]):
			errors.append("ending %s references unknown card '%s'" % [eid, endings[eid]["card"]])
	if strict_total:
		if cards.size() != EXPECTED_TOTAL:
			errors.append("card count is %d, expected exactly %d" % [cards.size(), EXPECTED_TOTAL])
		for cid in cards:
			if not inventory_ids.has(cid):
				errors.append("[%s] not present in CARD_INVENTORY.json" % cid)
	if fallback_count() == 0:
		errors.append("no fallback-pool cards defined; the selector cannot guarantee eligibility")


func fallback_count() -> int:
	var n := 0
	for cid in cards:
		if cards[cid].get("pool", "general") == "fallback":
			n += 1
	return n


func _build_indexes() -> void:
	var ids := cards.keys()
	ids.sort()
	for cid in ids:
		var card: Dictionary = cards[cid]
		_push(by_category, card["category"], cid)
		_push(by_speaker, card["speaker"], cid)
		var pool: String = card.get("pool", "general")
		_push(by_pool, pool, cid)
		if card.has("arc"):
			_push(by_arc, card["arc"]["id"], cid)
		for t in card.get("tags", []):
			if t.begins_with("res:"):
				_push(by_resource_tag, t.substr(4), cid)
		if pool == "fallback":
			fallback_cards.append(cid)
		elif pool == "general" or pool == "character" or pool == "crisis":
			if card.has("conditions") and not card["conditions"].is_empty():
				conditional_general.append(cid)
			else:
				unconditional_general.append(cid)


func _push(idx: Dictionary, key: String, cid: String) -> void:
	if not idx.has(key):
		idx[key] = []
	idx[key].append(cid)


func get_card(cid: String) -> Dictionary:
	return cards.get(cid, {})


func has_card(cid: String) -> bool:
	return cards.has(cid)


func get_character(cid: String) -> Dictionary:
	return characters.get(cid, {})


func search_cards(query: String) -> Array:
	var q := query.to_lower()
	var out: Array = []
	for cid in cards:
		var c: Dictionary = cards[cid]
		if cid.to_lower().contains(q) or str(c["text"]).to_lower().contains(q):
			out.append(cid)
	out.sort()
	return out
