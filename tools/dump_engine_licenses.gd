extends SceneTree
## Writes the Godot engine licence and bundled third-party copyright list to reports/licenses/.
## Run: godot --headless --path . --script tools/dump_engine_licenses.gd  (used by tools/build_credits.py)
func _init():
	var out := FileAccess.open("res://reports/licenses/godot_copyright.txt", FileAccess.WRITE)
	out.store_line("GODOT ENGINE LICENSE")
	out.store_line(Engine.get_license_text())
	out.store_line("")
	out.store_line("THIRD-PARTY COMPONENTS BUNDLED IN THE GODOT ENGINE BINARY")
	for c in Engine.get_copyright_info():
		out.store_line("")
		out.store_line("== " + str(c["name"]))
		for p in c["parts"]:
			for cp in p["copyright"]:
				out.store_line("  Copyright " + str(cp))
			out.store_line("  License: " + str(p["license"]))
	quit()
