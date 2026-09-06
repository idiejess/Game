extends Node
## Quick load-and-play smoke check: godot --headless --path . game/tests/Smoke.tscn
## Reloads content with strict_total disabled and plays 30 watches with a fixed seed.


func _ready() -> void:
	ContentDB.strict_total = false
	ContentDB.load_all()
	print("cards=%d errors=%d warnings=%d" % [ContentDB.cards.size(), ContentDB.errors.size(), ContentDB.warnings.size()])
	for e in ContentDB.errors.slice(0, 20):
		print("  ERR ", e)
	var tc := TurnController.new()
	tc.autosave = false
	tc.begin_run(4242)
	var i := 0
	while GameState.in_run() and i < 30:
		var card := ContentDB.get_card(tc.current_card_id)
		print("w%02d [%s] %s: %s" % [GameState.watch, CardSelector.last_selection_debug.get("source", "?"), tc.current_card_id, str(card.get("text", "")).left(70)])
		tc.decide("left" if i % 2 == 0 else "right")
		i += 1
	print("resources=", GameState.run["resources"], " ended=", GameState.run.get("ended"), " fallbacks=", GameState.run["fallback_count"])
	get_tree().quit(0 if ContentDB.errors.is_empty() else 1)
