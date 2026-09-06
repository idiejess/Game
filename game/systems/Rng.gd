class_name Rng
extends RefCounted
## Deterministic 32-bit LCG shared bit-for-bit with tools/simulate_runs.py.
## Kept in 32 bits so GDScript (64-bit int) and Python agree without wraparound tricks.

const A := 1664525
const C := 1013904223
const MASK := 0xFFFFFFFF

var state: int


func _init(seed_value: int = 1) -> void:
	state = (seed_value & MASK)
	if state == 0:
		state = 0x9E3779B9


func next_u32() -> int:
	state = (state * A + C) & MASK
	return state


## Float in [0, 1).
func next_float() -> float:
	return float(next_u32() >> 8) / float(1 << 24)


## Integer in [lo, hi] inclusive.
func next_int(lo: int, hi: int) -> int:
	if hi <= lo:
		return lo
	return lo + int(next_u32() % (hi - lo + 1))


## Weighted pick: returns index into weights, or -1 when total weight is zero.
func pick_weighted(weights: Array) -> int:
	var total := 0.0
	for w in weights:
		total += float(w)
	if total <= 0.0:
		return -1
	var r := next_float() * total
	var acc := 0.0
	for i in range(weights.size()):
		acc += float(weights[i])
		if r < acc:
			return i
	return weights.size() - 1
