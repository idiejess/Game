extends PanelContainer
## In-game developer panel (F1). Search/force cards, edit state, inspect eligibility and weights,
## show history, reload content, export state, reset progression.

var main
var search_box: LineEdit
var results: ItemList
var state_box: RichTextLabel
var res_edit: LineEdit
var flag_edit: LineEdit
var counter_edit: LineEdit
var rel_edit: LineEdit
var arc_edit: LineEdit
var run_edit: LineEdit
var ending_edit: LineEdit
var weights_box: RichTextLabel
var log_label: Label


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0, 0, 0, 0.93)
	add_theme_stylebox_override("panel", sb)
	var scroll := ScrollContainer.new()
	add_child(scroll)
	var box := VBoxContainer.new()
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(box)
	var title := Label.new()
	title.text = "DEVELOPER PANEL (F1 to close)"
	title.add_theme_color_override("font_color", UITheme.LAMP_AMBER)
	box.add_child(title)
	log_label = Label.new()
	log_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	log_label.add_theme_font_size_override("font_size", 22)
	box.add_child(log_label)

	# Search / force
	var row := HBoxContainer.new()
	box.add_child(row)
	search_box = LineEdit.new()
	search_box.placeholder_text = "search card id or text"
	search_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	search_box.text_changed.connect(_on_search)
	row.add_child(search_box)
	_btn(row, "Force selected", _force_selected)
	results = ItemList.new()
	results.custom_minimum_size = Vector2(0, 260)
	results.item_activated.connect(func(_i): _force_selected())
	box.add_child(results)

	# State editors
	res_edit = _field(box, "resource=value (e.g. water=12)", func(t): _set_kv(t, "resource"))
	rel_edit = _field(box, "character=value (e.g. vosk=80)", func(t): _set_kv(t, "relationship"))
	flag_edit = _field(box, "+flag / -flag (e.g. +found_ledger)", _set_flag)
	counter_edit = _field(box, "counter=value (e.g. suspicion=6)", func(t): _set_kv(t, "counter"))
	arc_edit = _field(box, "arc=stage[:status] (e.g. MA02=2:active)", _set_arc)
	run_edit = _field(box, "run number (e.g. 3)", _set_run)
	ending_edit = _field(box, "unlock ending id or unlock_ id (e.g. unlock_drays_key / end_true_river)", _unlock)

	var actions := HBoxContainer.new()
	box.add_child(actions)
	_btn(actions, "Refresh", refresh)
	_btn(actions, "Reload content", _reload)
	_btn(actions, "Export state", _export)
	_btn(actions, "Save now", func(): SaveManager.save(); _log("saved slot %d" % SaveManager.current_slot))
	_btn(actions, "Reset progression", _reset)
	_btn(actions, "New run", func(): main.start_new_run(); refresh())
	_btn(actions, "Asset review", func():
		var gallery = load("res://game/UI/AssetReview.gd").new()
		gallery.main = main
		main.add_child(gallery))

	var h := HBoxContainer.new()
	h.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(h)
	state_box = RichTextLabel.new()
	state_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	state_box.custom_minimum_size = Vector2(0, 700)
	state_box.add_theme_font_size_override("normal_font_size", 20)
	state_box.selection_enabled = true
	h.add_child(state_box)
	weights_box = RichTextLabel.new()
	weights_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	weights_box.custom_minimum_size = Vector2(0, 700)
	weights_box.add_theme_font_size_override("normal_font_size", 20)
	weights_box.selection_enabled = true
	h.add_child(weights_box)


func _btn(parent: Control, text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.add_theme_font_size_override("font_size", 22)
	b.pressed.connect(cb)
	parent.add_child(b)
	return b


func _field(parent: Control, placeholder: String, cb: Callable) -> LineEdit:
	var e := LineEdit.new()
	e.placeholder_text = placeholder
	e.add_theme_font_size_override("font_size", 22)
	e.text_submitted.connect(func(t):
		cb.call(t)
		e.text = ""
		refresh())
	parent.add_child(e)
	return e


func _log(msg: String) -> void:
	log_label.text = msg


func _on_search(q: String) -> void:
	results.clear()
	if q.strip_edges().length() < 2:
		return
	for cid in ContentDB.search_cards(q).slice(0, 60):
		var reason := CardSelector.eligibility_reason(cid) if GameState.in_run() else "no run"
		results.add_item("%s   [%s]   %s" % [cid, "eligible" if reason == "" else reason, str(ContentDB.cards[cid]["text"]).left(60)])


func _force_selected() -> void:
	var sel := results.get_selected_items()
	if sel.is_empty():
		return
	var cid := results.get_item_text(sel[0]).split("   ")[0]
	main.force_card(cid)
	_log("forced " + cid)
	refresh()


func _set_kv(t: String, kind: String) -> void:
	var parts := t.split("=")
	if parts.size() != 2 or not GameState.in_run():
		_log("format key=value (needs an active run)")
		return
	var k := parts[0].strip_edges()
	var v := int(parts[1].strip_edges())
	match kind:
		"resource":
			GameState.set_resource(k, v)
			GameState.resources_changed.emit({k: 0})
		"relationship":
			GameState.run["relationships"][k] = clamp(v, 0, 100)
		"counter":
			GameState.set_counter(k, v)
	_log("%s %s = %d" % [kind, k, v])


func _set_flag(t: String) -> void:
	t = t.strip_edges()
	if t.length() < 2:
		return
	var on := not t.begins_with("-")
	var f := t.trim_prefix("+").trim_prefix("-")
	if not ContentDB.flags.has(f):
		_log("undeclared flag " + f)
		return
	GameState.set_flag(f, on)
	_log(("set " if on else "cleared ") + f)


func _set_arc(t: String) -> void:
	var parts := t.split("=")
	if parts.size() != 2:
		return
	var rest := parts[1].split(":")
	GameState.set_arc(parts[0].strip_edges(), int(rest[0]), rest[1] if rest.size() > 1 else "active")
	_log("arc %s -> %s" % [parts[0], parts[1]])


func _set_run(t: String) -> void:
	GameState.profile["run_number"] = max(1, int(t))
	_log("run number = %d" % GameState.run_number())


func _unlock(t: String) -> void:
	t = t.strip_edges()
	if t.begins_with("unlock_"):
		GameState.grant_unlock(t)
		_log("granted " + t)
	elif ContentDB.endings.has(t):
		GameState.profile["endings"].append({"id": t, "run": GameState.run_number(), "watch": GameState.watch})
		_log("recorded ending " + t)
	else:
		_log("unknown " + t)


func _reload() -> void:
	var ok := ContentDB.load_all()
	_log("content reloaded: %s (%d cards, %d errors)" % ["ok" if ok else "ERRORS", ContentDB.cards.size(), ContentDB.errors.size()])
	refresh()


func _export() -> void:
	var path := "user://state_export.json"
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string(SaveManager.export_state_text())
	f.close()
	DisplayServer.clipboard_set(SaveManager.export_state_text())
	_log("exported to %s and clipboard" % ProjectSettings.globalize_path(path))


func _reset() -> void:
	SaveManager.delete_slot(SaveManager.current_slot)
	GameState.reset_profile()
	main._ended = true
	_log("progression reset")
	refresh()


func refresh() -> void:
	var gs = GameState
	var s := "[b]Run %d  Watch %d  Seed %s[/b]\n" % [gs.run_number(), gs.watch, str(gs.run.get("seed", "-"))]
	s += "Content: %d cards, %d chars, %d endings, loaded=%s\n" % [ContentDB.cards.size(), ContentDB.characters.size(), ContentDB.endings.size(), str(ContentDB.loaded)]
	if gs.in_run():
		s += "Resources: %s\n" % str(gs.run["resources"])
		s += "Relationships: %s\n" % str(gs.run["relationships"])
		s += "Factions: %s\n" % str(gs.run["factions"])
		s += "Flags: %s\n" % str(gs.run["flags"])
		var nz := {}
		for c in gs.run["counters"]:
			if int(gs.run["counters"][c]) != 0:
				nz[c] = gs.run["counters"][c]
		s += "Counters (non-zero): %s\n" % str(nz)
		s += "Arcs: %s\n" % str(gs.run["arcs"])
		s += "Forced: %s  Delayed: %s  Subdecks: %d  Fallbacks: %d\n" % [str(gs.run["forced_queue"]), str(gs.run["delayed"]), gs.run["subdecks"].size(), int(gs.run.get("fallback_count", 0))]
		s += "Last selection: %s\n" % str(CardSelector.last_selection_debug)
		s += "[b]Recent history[/b]\n"
		for h in gs.recent_history(12):
			s += "  w%d %s → %s\n" % [int(h["watch"]), h["card"], h["choice"]]
	s += "[b]Profile[/b] unlocks=%s\nlore=%s\nendings=%d discovered=%d pflags=%s\n" % [str(gs.profile["unlocks"]), str(gs.profile["lore"]), gs.profile["endings"].size(), gs.profile["discovered_cards"].size(), str(gs.profile["persistent_flags"])]
	state_box.text = s
	var w := "[b]Top weights now[/b]\n"
	if gs.in_run():
		for e in CardSelector.explain_all(40):
			if e["weight"] > 0.0:
				w += "%6.2f  %s\n" % [e["weight"], e["id"]]
			else:
				w += "   --   %s  (%s)\n" % [e["id"], e["reason"]]
	weights_box.text = w
