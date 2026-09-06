extends Node
## Headless test runner: godot --headless --path . game/tests/TestRunner.tscn
## Writes reports/validation/engine_tests.json and exits non-zero on failure.

var results: Array = []
var failures := 0
var root: Node


func _ready() -> void:
	root = get_tree().root
	var tests = load("res://game/tests/EngineTests.gd").new()
	tests.runner = self
	for m in tests.get_method_list():
		var n: String = m["name"]
		if n.begins_with("test_"):
			_run_one(tests, n)
	_write_report()
	print("\n%d checks, %d failures" % [results.size(), failures])
	get_tree().quit(1 if failures > 0 else 0)


func _run_one(obj, name: String) -> void:
	var before := failures
	obj.current = name
	obj.call(name)
	var ok := failures == before
	print("%s %s" % ["PASS" if ok else "FAIL", name])


func check(cond: bool, test: String, msg: String) -> void:
	results.append({"test": test, "ok": cond, "message": msg})
	if not cond:
		failures += 1
		printerr("  FAIL [%s] %s" % [test, msg])


func _write_report() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://reports/validation"))
	var f := FileAccess.open("res://reports/validation/engine_tests.json", FileAccess.WRITE)
	f.store_string(JSON.stringify({"generated": Time.get_datetime_string_from_system(true), "total": results.size(),
		"failures": failures, "results": results}, "  "))
