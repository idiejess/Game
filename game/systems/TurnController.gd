class_name TurnController
extends RefCounted
## Drives one run: draws cards, applies decisions, advances watches, fires endings, autosaves.
## Used by both the UI (Main.gd) and headless tests. No scene dependencies.

signal card_drawn(card_id: String)
signal decision_applied(card_id: String, side: String, report: Dictionary)
signal ending_fired(ending_id: String)

var current_card_id := ""
var autosave := true
var pending_ending := ""   # set when an edge/trigger fires; the ending card is shown first


func begin_run(seed_value: int = -1) -> void:
	pending_ending = ""
	GameState.start_run(seed_value)
	# Every run opens with the first onboarding card if it exists; the Ledger meta cards follow by weight.
	if ContentDB.has_card("onb_01") and GameState.run_number() >= 1:
		GameState.run["forced_queue"].append("onb_01")
	if GameState.run_number() >= 2 and ContentDB.has_card("meta_new_keeper_2"):
		GameState.run["forced_queue"].append("meta_new_keeper_2")
	draw()


func resume_run() -> void:
	pending_ending = str(GameState.run.get("pending_ending", ""))
	var cur = GameState.run.get("current_card", null)
	if cur != null and ContentDB.has_card(str(cur)):
		current_card_id = str(cur)
		card_drawn.emit(current_card_id)
	else:
		draw()


func draw() -> String:
	if not GameState.in_run():
		return ""
	var cid := CardSelector.next_card()
	if cid == "":
		return ""
	current_card_id = cid
	GameState.record_card_shown(cid)
	if autosave:
		SaveManager.save()
	card_drawn.emit(cid)
	return cid


## side is "left" or "right".
func decide(side: String) -> Dictionary:
	if current_card_id == "" or not GameState.in_run():
		return {}
	var card := ContentDB.get_card(current_card_id)
	var choice: Dictionary = card[side]
	var cid := current_card_id
	var report := GameState.apply_effects(choice["effects"], cid)
	GameState.record_decision(cid, side)
	if card.has("arc") and GameState.arc_status(card["arc"]["id"]) == "inactive":
		GameState.set_arc(card["arc"]["id"], int(card["arc"]["stage"]), "active")
	elif card.has("arc") and GameState.arc_status(card["arc"]["id"]) == "active":
		GameState.set_arc(card["arc"]["id"], max(GameState.arc_stage(card["arc"]["id"]), int(card["arc"]["stage"])))
	decision_applied.emit(cid, side, report)
	current_card_id = ""
	if pending_ending != "":
		# The ending card itself was just resolved.
		var e := pending_ending
		pending_ending = ""
		_fire_ending(e)
		return report
	var ending: String = report.get("ending", "")
	if ending == "":
		ending = GameState.advance_watch()
	if ending == "":
		ending = GameState.check_triggered_endings()
	if ending == "" and GameState.watch >= GameState.LONG_WATCH and not GameState.has_flag("allies_gathered"):
		ending = GameState.long_watch_ending()
	if ending != "":
		_stage_ending(ending)
		return report
	if autosave:
		SaveManager.save()
	draw()
	return report


## Shows the ending's card before the ending screen, so the last moment is still a decision.
func _stage_ending(ending_id: String) -> void:
	var e: Dictionary = ContentDB.endings.get(ending_id, {})
	var card_id: String = str(e.get("card", ""))
	if card_id != "" and ContentDB.has_card(card_id):
		pending_ending = ending_id
		GameState.run["forced_queue"].push_front(card_id)
		GameState.run["pending_ending"] = ending_id
		draw()
	else:
		_fire_ending(ending_id)


func _fire_ending(ending_id: String) -> void:
	if not ContentDB.endings.has(ending_id):
		push_error("[TurnController] unknown ending %s; using dismissal" % ending_id)
		ending_id = "end_res_company_min" if ContentDB.endings.has("end_res_company_min") else ending_id
	GameState.end_run(ending_id)
	if autosave:
		SaveManager.save()
	ending_fired.emit(ending_id)


## Preview of a choice's resource direction for the UI. Returns {resource: delta}.
static func preview(card: Dictionary, side: String) -> Dictionary:
	return card[side]["effects"].get("resources", {})
