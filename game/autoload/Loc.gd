extends Node
## Localization. Card text is authored in JSON and mirrored to content/localization/<lang>.csv
## by tools/generate_reports.py --localization. UI strings live in the CSV under ui.*.
## tr_key() falls back to the English source text so missing keys never show raw keys to players.

var strings: Dictionary = {}
var lang := "en"
var missing: Dictionary = {}


func _ready() -> void:
	lang = str(Settings.get_value("language"))
	load_language(lang)


func load_language(code: String) -> void:
	strings.clear()
	lang = code
	# ui_<lang>.csv is hand-authored; cards_<lang>.csv is generated from the card JSON.
	var found := false
	for base in ["ui_%s.csv", "cards_%s.csv"]:
		var path: String = "res://content/localization/" + (base % code)
		if not FileAccess.file_exists(path):
			continue
		found = true
		var f := FileAccess.open(path, FileAccess.READ)
		var header := true
		while not f.eof_reached():
			var row := f.get_csv_line()
			if header:
				header = false
				continue
			if row.size() >= 2 and row[0] != "":
				strings[row[0]] = row[1]
	if not found:
		push_warning("[Loc] no localization files for %s" % code)


## UI string by key; `fallback` is shown if the key is absent.
func ui(key: String, fallback: String = "") -> String:
	var k := "ui." + key
	if strings.has(k):
		return strings[k]
	missing[k] = true
	return fallback if fallback != "" else key


## Card field with fallback to the authored text.
func card_text(card: Dictionary, field: String, source_text: String) -> String:
	var prefix: String = card.get("loc_key", "card." + card["id"])
	var k := prefix + "." + field
	if strings.has(k) and lang != "en":
		return strings[k]
	return source_text
