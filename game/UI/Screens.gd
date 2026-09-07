class_name Screens
extends RefCounted
## Factory for full-screen overlays: title, pause, settings, history, objectives, gallery,
## archive (lore), ending history, save slots, credits, content warning, ending, content error.
## All screens are keyboard navigable (buttons take focus; the first control grabs focus).


static func make(name: String, main, args: Dictionary) -> Control:
	var root := _overlay(name not in ["ending", "title", "content_warning", "content_error"])
	var scroll := ScrollContainer.new()
	scroll.set_anchors_preset(Control.PRESET_FULL_RECT)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	root.add_child(scroll)
	var margin := MarginContainer.new()
	margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 40)
	scroll.add_child(margin)
	var box := VBoxContainer.new()
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_theme_constant_override("separation", 20)
	margin.add_child(box)
	match name:
		"title": _title(box, main)
		"pause": _pause(box, main)
		"settings": _settings(box, main)
		"history": _history(box, main)
		"objectives": _objectives(box, main)
		"gallery": _gallery(box, main)
		"archive": _archive(box, main)
		"endings": _endings(box, main)
		"slots": _slots(box, main, args)
		"credits": _credits(box, main)
		"content_warning": _content_warning(box, main)
		"ending": _ending(box, main, args)
		"content_error": _content_error(box, main)
		_: _label(box, "Unknown screen " + name)
	# Focus the first button for keyboard users.
	root.ready.connect(func():
		for c in _walk(box):
			if c is Button:
				c.grab_focus()
				break)
	return root


static func _first_existing(paths: Array) -> String:
	for p in paths:
		if ResourceLoader.exists(p):
			return p
	return ""


static func _walk(n: Node) -> Array:
	var out := [n]
	for c in n.get_children():
		out += _walk(c)
	return out


static func _overlay(translucent: bool = true) -> Control:
	var root := PanelContainer.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.06, 0.1, 0.1, 0.94 if translucent else 1.0)
	root.add_theme_stylebox_override("panel", sb)
	root.mouse_filter = Control.MOUSE_FILTER_STOP
	return root


static func _title_label(box: Control, text: String) -> Label:
	var l := Label.new()
	l.text = text
	l.theme_type_variation = "TitleLabel"
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(l)
	return l


static func _label(box: Control, text: String, small: bool = false) -> Label:
	var l := Label.new()
	l.text = text
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	if small:
		l.theme_type_variation = "SmallLabel"
	box.add_child(l)
	return l


static func _button(box: Control, text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(0, 96)
	b.pressed.connect(cb)
	box.add_child(b)
	return b


static func _back(box: Control, main, target: String = "pause") -> void:
	_button(box, Loc.ui("back", "Back"), func():
		if target == "close":
			main._close_screens()
		else:
			main._show_screen(target))


# ------------------------------------------------------------------ screens
static func _title(box: Control, main) -> void:
	_title_label(box, Loc.ui("title", "HALFWAY LOCK"))
	_label(box, Loc.ui("subtitle", "Keeper of the Meridian Canal"), true)
	var summary := SaveManager.slot_summary(SaveManager.current_slot)
	if summary.get("in_run", false):
		_button(box, Loc.ui("continue", "Continue") + "  (%s %d)" % [Loc.ui("watch", "Watch"), int(summary["watch"])], func(): main.continue_run())
	_button(box, Loc.ui("new_run", "New Keeper"), func(): main.start_new_run())
	_button(box, Loc.ui("save_slots", "Save Slots"), func(): main._show_screen("slots", {"from": "title"}))
	_button(box, Loc.ui("archive", "Ledger Archive"), func(): main._show_screen("archive"))
	_button(box, Loc.ui("gallery", "Characters"), func(): main._show_screen("gallery"))
	_button(box, Loc.ui("endings", "Ending History"), func(): main._show_screen("endings"))
	_button(box, Loc.ui("settings", "Settings"), func(): main._show_screen("settings"))
	_button(box, Loc.ui("credits", "Credits"), func(): main._show_screen("credits"))
	var rn := int(GameState.profile.get("run_number", 0))
	_label(box, "%s: %d   %s: %d / %d   %s: %d" % [Loc.ui("keepers", "Keepers"), rn, Loc.ui("cards_seen", "Cards seen"),
		GameState.profile["discovered_cards"].size(), ContentDB.cards.size(), Loc.ui("endings_count", "Endings"),
		GameState.profile["endings"].size()], true)
	_label(box, Loc.ui("placeholder_notice", "Preview build: art and audio are candidates awaiting final production."), true)


static func _pause(box: Control, main) -> void:
	_title_label(box, Loc.ui("paused", "Paused"))
	_button(box, Loc.ui("resume", "Resume"), func(): main._close_screens())
	_button(box, Loc.ui("history", "History"), func(): main._show_screen("history"))
	_button(box, Loc.ui("objectives", "Objectives"), func(): main._show_screen("objectives"))
	_button(box, Loc.ui("gallery", "Characters"), func(): main._show_screen("gallery"))
	_button(box, Loc.ui("archive", "Ledger Archive"), func(): main._show_screen("archive"))
	_button(box, Loc.ui("settings", "Settings"), func(): main._show_screen("settings"))
	_button(box, Loc.ui("abandon", "Abandon Keeper"), func():
		if GameState.in_run():
			GameState.end_run("end_res_company_min")
			SaveManager.save()
		main._ended = true
		main._show_screen("title"))
	_button(box, Loc.ui("to_title", "Title Screen"), func(): main._show_screen("title"))


static func _toggle(box: Control, label: String, key: String) -> void:
	var cb := CheckButton.new()
	cb.text = label
	cb.button_pressed = bool(Settings.get_value(key))
	cb.custom_minimum_size = Vector2(0, 80)
	cb.toggled.connect(func(v): Settings.set_value(key, v))
	box.add_child(cb)


static func _slider(box: Control, label: String, key: String, lo: float, hi: float, step: float) -> void:
	var h := HBoxContainer.new()
	box.add_child(h)
	var l := Label.new()
	l.text = label
	l.custom_minimum_size = Vector2(300, 0)
	h.add_child(l)
	var s := HSlider.new()
	s.min_value = lo
	s.max_value = hi
	s.step = step
	s.value = float(Settings.get_value(key))
	s.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	s.custom_minimum_size = Vector2(0, 60)
	s.focus_mode = Control.FOCUS_ALL
	var val := Label.new()
	val.text = "%.1f" % s.value
	s.value_changed.connect(func(v):
		val.text = "%.1f" % v
		Settings.set_value(key, v))
	h.add_child(s)
	h.add_child(val)


static func _settings(box: Control, main) -> void:
	_title_label(box, Loc.ui("settings", "Settings"))
	_label(box, Loc.ui("settings_access", "Accessibility"), true)
	_slider(box, Loc.ui("text_size", "Text size"), "text_scale", 0.8, 1.6, 0.1)
	_toggle(box, Loc.ui("high_contrast", "High contrast"), "high_contrast")
	_toggle(box, Loc.ui("reduced_motion", "Reduced motion"), "reduced_motion")
	_toggle(box, Loc.ui("screen_shake", "Screen shake"), "screen_shake")
	_toggle(box, Loc.ui("show_buttons", "Show decision buttons"), "show_buttons")
	_toggle(box, Loc.ui("confirm_decisions", "Confirm decisions"), "confirm_decisions")
	_toggle(box, Loc.ui("exact_effects", "Show exact effects"), "show_exact_effects")
	_toggle(box, Loc.ui("subtitles", "Subtitles for audio cues"), "subtitles")
	_label(box, Loc.ui("settings_audio", "Audio"), true)
	_slider(box, Loc.ui("music", "Music"), "music_volume", 0.0, 1.0, 0.1)
	_slider(box, Loc.ui("sfx", "Sound"), "sfx_volume", 0.0, 1.0, 0.1)
	_button(box, Loc.ui("reset_settings", "Reset settings"), func(): Settings.reset_defaults(); main._show_screen("settings"))
	_back(box, main, "pause" if GameState.in_run() and main.game_layer.visible else "title")


static func _history(box: Control, main) -> void:
	_title_label(box, Loc.ui("history", "History"))
	var h: Array = GameState.run.get("history", [])
	if h.is_empty():
		_label(box, Loc.ui("history_empty", "No decisions yet this watch."))
	# Newest first, at most 40 entries; the stop index is exclusive.
	for i in range(h.size() - 1, max(-1, h.size() - 41), -1):
		var rec: Dictionary = h[i]
		var card := ContentDB.get_card(rec["card"])
		if card.is_empty():
			continue
		var ch := ContentDB.get_character(card["speaker"])
		var l := _label(box, "%s %d  %s: %s\n   → %s" % [Loc.ui("watch", "Watch"), int(rec["watch"]), ch.get("name", ""),
			Loc.card_text(card, "text", card["text"]), Loc.card_text(card, rec["choice"], card[rec["choice"]]["label"])], true)
	_back(box, main)


static func _objectives(box: Control, main) -> void:
	_title_label(box, Loc.ui("objectives", "Objectives"))
	var objectives := [
		["obj_survive_20", "Keep the gate for twenty watches.", GameState.watch >= 20],
		["obj_meet_all", "Meet all twelve of the summit's people.", GameState.profile["discovered_characters"].size() >= 12],
		["obj_notice_water", "Notice what the gauge is telling you.", GameState.has_flag("noticed_water_fall") or GameState.profile["lore"].size() > 0],
		["obj_key", "Find what Dray left behind.", GameState.has_unlock("unlock_drays_key")],
		["obj_survey", "Learn what the reservoirs cannot explain.", GameState.has_unlock("unlock_quenn_survey")],
		["obj_song", "Hear the whole of the Lowmere Song.", GameState.has_unlock("unlock_lowmere_song")],
		["obj_letters", "Read what the chapel keeps under the water.", GameState.has_unlock("unlock_marrow_letters")],
		["obj_map", "Map the Cut.", GameState.has_unlock("unlock_cut_map")],
		["obj_true", "Decide what the water is for.", GameState.profile["persistent_flags"].has("p_true_ending_seen")],
	]
	for o in objectives:
		_label(box, ("☑ " if o[2] else "☐ ") + o[1])
	var active := []
	for a in GameState.run.get("arcs", {}):
		if GameState.arc_status(a) == "active":
			var title: String = GameState.run["arcs"][a].get("title", a)
			var g: Dictionary = ContentDB.story_graph.get("major_arcs", {}).get(a, ContentDB.story_graph.get("minor_arcs", {}).get(a, {}))
			active.append("%s (stage %d)" % [g.get("title", a), GameState.arc_stage(a)])
	if not active.is_empty():
		_label(box, Loc.ui("active_threads", "Open threads"), true)
		for s in active:
			_label(box, "• " + s)
	_back(box, main)


static func _gallery(box: Control, main) -> void:
	_title_label(box, Loc.ui("gallery", "Characters"))
	var discovered: Array = GameState.profile["discovered_characters"]
	var ids := ContentDB.characters.keys()
	ids.sort()
	for cid in ids:
		var ch: Dictionary = ContentDB.characters[cid]
		if ch["tier"] == "source":
			continue
		if discovered.has(cid):
			var row := HBoxContainer.new()
			box.add_child(row)
			var bar := ColorRect.new()
			bar.color = UITheme.faction_color(ch["faction"])
			bar.custom_minimum_size = Vector2(12, 60)
			row.add_child(bar)
			var v := VBoxContainer.new()
			v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row.add_child(v)
			_label(v, "%s — %s" % [ch["name"], ch["role"]])
			var rel := GameState.get_relationship(cid) if GameState.in_run() else -1
			var extra := ("  ·  " + Loc.ui("regard", "Regard") + ": " + _rel_word(rel)) if rel >= 0 else ""
			_label(v, str(ch.get("silhouette", "")) + extra, true)
		else:
			_label(box, "— " + Loc.ui("undiscovered", "Not yet met") + " —", true)
	_back(box, main, "pause" if GameState.in_run() and main.game_layer.visible else "title")


static func _rel_word(v: int) -> String:
	if v >= 75: return Loc.ui("rel.trusted", "trusted")
	if v >= 55: return Loc.ui("rel.warm", "warm")
	if v >= 40: return Loc.ui("rel.civil", "civil")
	if v >= 25: return Loc.ui("rel.cold", "cold")
	return Loc.ui("rel.hostile", "hostile")


static func _archive(box: Control, main) -> void:
	_title_label(box, Loc.ui("archive", "Ledger Archive"))
	_label(box, Loc.ui("archive_intro", "What the Keepers of Halfway have written down, and passed on."), true)
	var lore: Array = GameState.profile["lore"]
	var unlocks: Array = GameState.profile["unlocks"]
	if lore.is_empty() and unlocks.is_empty():
		_label(box, Loc.ui("archive_empty", "The Ledger is blank. Watch the water."))
	for u in unlocks:
		_label(box, "◆ " + Loc.ui("unlock." + u, u.trim_prefix("unlock_").replace("_", " ").capitalize()))
	for l in lore:
		_label(box, "• " + Loc.ui("lore." + l, l.trim_prefix("lore_").replace("_", " ").capitalize()), true)
	_back(box, main, "pause" if GameState.in_run() and main.game_layer.visible else "title")


static func _endings(box: Control, main) -> void:
	_title_label(box, Loc.ui("endings", "Ending History"))
	var seen: Array = GameState.profile["endings"]
	var by_id := {}
	for rec in seen:
		by_id[rec["id"]] = int(by_id.get(rec["id"], 0)) + 1
	var ids := ContentDB.endings.keys()
	ids.sort()
	var kinds := {"resource_death": "Failures", "ordinary": "Ordinary endings", "false": "False conclusions", "revelation": "Revelations", "crisis": "Crises", "true": "True endings"}
	for kind in kinds:
		_label(box, kinds[kind], true)
		for eid in ids:
			var e: Dictionary = ContentDB.endings[eid]
			if e["kind"] != kind:
				continue
			if by_id.has(eid):
				_label(box, "%s  ×%d\n   %s" % [e["title"], by_id[eid], e["epilogue"]])
			else:
				_label(box, "???", true)
	_back(box, main, "title")


static func _slots(box: Control, main, args: Dictionary) -> void:
	_title_label(box, Loc.ui("save_slots", "Save Slots"))
	for slot in range(1, SaveManager.SLOT_COUNT + 1):
		var s := SaveManager.slot_summary(slot)
		var desc := Loc.ui("empty_slot", "Empty")
		if not s.is_empty():
			desc = "%s %d · %d %s · %s" % [Loc.ui("keeper", "Keeper"), int(s["run_number"]), int(s["endings"]), Loc.ui("endings_count", "Endings").to_lower(),
				(Loc.ui("in_progress", "in progress") if s["in_run"] else Loc.ui("between_runs", "between runs"))]
		var row := HBoxContainer.new()
		box.add_child(row)
		var b := Button.new()
		b.text = "%s %d%s — %s" % [Loc.ui("slot", "Slot"), slot, (" ●" if slot == SaveManager.current_slot else ""), desc]
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.custom_minimum_size = Vector2(0, 96)
		b.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		b.pressed.connect(func():
			# Persist the slot being left, unless it holds nothing yet (avoids writing an empty
			# "Keeper 0" file over an unused slot).
			if int(GameState.profile.get("run_number", 0)) > 0 or GameState.in_run():
				SaveManager.save()
			SaveManager.load(slot)
			main._ended = true
			main._show_screen("title"))
		row.add_child(b)
		var del := Button.new()
		del.text = "✕"
		del.tooltip_text = Loc.ui("delete", "Delete")
		del.custom_minimum_size = Vector2(96, 96)
		del.pressed.connect(func():
			SaveManager.delete_slot(slot)
			if slot == SaveManager.current_slot:
				GameState.reset_profile()
				# The run shown behind the title belongs to the deleted profile.
				main._ended = true
			main._show_screen("slots", args))
		row.add_child(del)
	_back(box, main, "title")


static func _credits(box: Control, main) -> void:
	_title_label(box, Loc.ui("credits", "Credits"))
	_label(box, Loc.ui("credits_line1", "HALFWAY LOCK — Keeper of the Meridian Canal"))
	_label(box, Loc.ui("credits_line2", "An original narrative decision game. Design, writing, code, art and audio were produced for this project; nothing is borrowed from another game."), true)
	_label(box, Loc.ui("credits_line3", "Built with Godot Engine 4 (MIT licence). Full third-party notices ship as THIRD_PARTY_NOTICES.md; asset provenance is in CREDITS.md."), true)
	_label(box, Loc.ui("credits_line4", "Art and audio in this build are original procedural candidates awaiting final production."), true)
	_label(box, Loc.ui("credits_line5", "Content warnings: death and drowning (described, not depicted); displacement; alcohol; institutional injustice."), true)
	_label(box, Loc.ui("credits_line6", "Privacy: the game stores settings and saves on this device only and sends nothing anywhere."), true)
	_back(box, main, "title")


static func _content_warning(box: Control, main) -> void:
	_title_label(box, Loc.ui("content_warning", "Before you begin"))
	_label(box, Loc.ui("content_warning_text", "Halfway Lock is a story about a canal, a town and the people who depend on both. It includes death and drowning described in text, displacement of a community, alcohol, and institutions behaving badly. Nothing is depicted graphically. Suitable for ages 13 and up."))
	_label(box, Loc.ui("controls_text", "Drag the card left or right, press the buttons beneath it, or use A/D or the arrow keys. Escape pauses."), true)
	_button(box, Loc.ui("understood", "Understood"), func():
		Settings.set_value("content_warnings_seen", true)
		main._show_screen("title"))


static func _ending(box: Control, main, args: Dictionary) -> void:
	var eid: String = args.get("ending", "")
	var e: Dictionary = ContentDB.endings.get(eid, {})
	var kind := str(e.get("kind", ""))
	_label(box, {"true": "A TRUE ENDING", "revelation": "THE LEDGER GROWS", "false": "AN ENDING, OF SORTS"}.get(kind, "THE KEEPER'S WATCH ENDS"), true)
	_title_label(box, str(e.get("title", eid)))
	# Illustration: the ending's own picture when produced, else its background variant. Missing
	# files are skipped so an incomplete asset pass never breaks the screen.
	var art := _first_existing(["res://assets/endings/ending_%s.png" % eid.trim_prefix("end_"),
		"res://assets/backgrounds/bg_ending_%s.png" % ("true" if kind == "true" else ("fail" if kind in ["resource_death", "crisis"] else "true")),
		"res://assets/backgrounds/bg_pound_night.png"])
	if art != "":
		var tex := TextureRect.new()
		tex.texture = load(art)
		tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		tex.custom_minimum_size = Vector2(0, 260)
		tex.clip_contents = true
		tex.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		box.add_child(tex)
	_label(box, str(e.get("epilogue", "")))
	_label(box, "%s %d · %s %d" % [Loc.ui("keeper", "Keeper"), GameState.run_number(), Loc.ui("watches_kept", "watches kept:"), GameState.watch], true)
	var new_unlocks: Array = e.get("unlocks", [])
	if not new_unlocks.is_empty():
		_label(box, Loc.ui("ledger_records", "The Ledger now records:"), true)
		for u in new_unlocks:
			_label(box, "◆ " + Loc.ui("unlock." + u, u.trim_prefix("unlock_").replace("_", " ").capitalize()))
	_button(box, Loc.ui("next_keeper", "The next Keeper"), func(): main.start_new_run())
	_button(box, Loc.ui("archive", "Ledger Archive"), func(): main._show_screen("archive"))
	_button(box, Loc.ui("to_title", "Title Screen"), func(): main._show_screen("title"))


static func _content_error(box: Control, main) -> void:
	_title_label(box, "Content failed to load")
	_label(box, "The card library did not validate. This build cannot start. Errors:")
	for e in ContentDB.errors.slice(0, 30):
		_label(box, "• " + e, true)
	_button(box, "Retry", func():
		if ContentDB.load_all():
			main._show_screen("title")
		else:
			main._show_screen("content_error"))
