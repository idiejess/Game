# Narrative System — Halfway Lock

How the engine turns 1,000 data cards into a run. Implementation: `game/autoload/CardSelector.gd`,
`game/autoload/GameState.gd`, `game/systems/TurnController.gd`, `game/systems/Conditions.gd`.
The Python simulator `tools/simulate_runs.py` mirrors every rule here bit-for-bit; the engine test
`test_engine_matches_python_simulator` fails if they drift.

## 1. One watch
1. `CardSelector.next_card()` picks a card (§2). `GameState.record_card_shown` increments its appearance count.
2. The player decides left or right. `GameState.apply_effects` applies resources, relationships, factions,
   flags, counters, forced follow-ups, delayed cards, delayed resources, sub-decks, arc state, unlocks,
   lore, objectives and any explicit `ending` (with optional `ending_chance`).
3. `TurnController` records the decision, activates/advances the card's arc (§4), then:
   - `GameState.advance_watch()` — watch += 1, water drift (§5), cooldown tick, due delayed resources,
     resource edge check (§6.1);
   - `GameState.check_triggered_endings()` — false/crisis endings (§6.2);
   - at watch ≥ 100 without `allies_gathered`, `GameState.long_watch_ending()` (§6.3).
4. An ending is *staged*: its `endings_meta` card is forced next; resolving that card fires the ending,
   records it in the profile, grants unlocks/lore and persistent flags, and autosaves.

## 2. Selection order
1. **Forced queue** (`followup`, ending cards, engine openers `onb_01` / `meta_new_keeper_2`).
2. **Due delayed cards**, earliest due first. A due card whose conditions fail is postponed 3 watches,
   at most `MAX_DELAY_POSTPONES` (3) times, then dropped with a warning.
3. **Active sub-decks** honouring `interleave`.
4. **Weighted pool**: candidates are `general`/`character`/`crisis` cards (index order: unconditional
   first, then conditional, each sorted by id). Crisis-pool cards are only candidates on Ledger Days
   (every 20th watch), when any resource is in a danger band (≤30 or ≥70), or every 7th watch.
   Onboarding cards leave the pool after watch 14.
5. **Fallback pool** when nothing is eligible (counted; a warning is raised when the library is large).

### Eligibility (`CardSelector.eligibility_reason`)
Forced-only and ending-only pools are never eligible by weight; cooldown; `max_per_run` (default 1);
currently shown; arc completed/failed; then every `conditions` block (flags, resources, relationships,
factions, counters, run number, watch, seen/unseen cards, unlocks, arc stage/status, endings seen).

### Weight (`CardSelector.weight_for`)
`weight` × each satisfied `weight_mods.multiply` × crisis factor (Ledger Day ×4, danger-relevant ×1.5,
otherwise ×0.15) × resource-danger bonus (×2.5 per matching `res:<x>` tag) × arc-active bonus (×5 for
the next stage of an active arc) × repeat penalty (×0.25 if seen this run) or undiscovered bonus
(×1.6 if never seen in any run) × same-speaker penalty (×0.4, not for arc cards) × recent-category
penalty (×0.6) × late-onboarding penalty (×0.05 after watch 12).

## 3. Determinism
`Rng` is a 32-bit LCG (a=1664525, c=1013904223). One stream per run, seeded by `run.seed`, consumed by
weighted picks, fallback picks, `delay_max`, `ending_chance`, sub-deck shuffles and the simulator's
random strategy. `run.rng_state` is saved after every pick and restored on load, so a loaded run
continues the exact card sequence an uninterrupted run would have produced (tested).

## 4. Arcs
Major arcs: 15 cards, 5 stages × 3; minor arcs: 6 cards, 6 stages × 1. Any arc card resolved while the
arc is inactive activates it at that card's stage; later cards raise the stage. Stage N cards require
`arc_stage: {ARC: {min: N-1}}` (within a stage the first card opens it and the others require its
flag). `arc: {ARC: {status: completed|failed}}` closes the arc and removes its cards from selection.
Arcs may be interrupted by anything and resume because state lives in `run.arcs`.
`tools/audit_arcs.py` checks every arc statically (entry, contiguous stages, prerequisites set by
earlier stages or by cards outside the arc, completion route, true-route prerequisites).

## 5. Water drift
Per watch: −1 (`WATER_DRIFT`) + `water_drift_mod` counter; −1 more with `gates_leaking`; +1 with
`wet_season`; **+1 when Traffic ≤ 35, −1 more when Traffic ≥ 70** (the gate spends water for traffic);
`sluice_rebuilt` stops drift entirely. The traffic coupling was added during balance (D-009).

## 6. Ending triggers (data-driven, `content/endings/endings.json`)
1. **Resource edge**: a resource at 0 or 100 fires the first ending in file order whose
   `trigger.resource_edge` matches and whose `trigger.conditions` hold (revelation endings such as
   `end_rev_sluice`); the plain `end_res_<r>_<edge>` is the fallback.
2. **Conditions**: endings with `trigger.conditions` (and optional `watch_min`) are checked after every
   watch; first satisfied wins. Used by false endings (`end_false_*`) and crisis endings (`end_crisis_*`).
3. **Long watch**: at watch 100, `trigger.long_watch: true` candidates are tried in file order
   (Jubilee, Tobin's story, A Quiet Life, Town's/Company's Keeper, Transferred); `end_ord_long_watch`
   (`watch_min` only) is the fallback. MA12 (`allies_gathered`) suspends the retirement.
4. **Card-fired**: `effects.ending` on a card (true endings, The Drought Report).
The validator rejects an ending that has neither a trigger nor a card firing it.

## 7. Persistent progression
`profile` survives runs: run number, unlocks, lore, objectives, endings (records), discovered cards
and characters, persistent counters/flags (`p_*`), achievements, total watches. `end_run` derives
persistent flags from the run (e.g. `honored_remembered` → `p_honored_remembered`) and
`start_run` applies openers (Quenn +10, Hullfolk +8). Saves are versioned (v2) with migration.
