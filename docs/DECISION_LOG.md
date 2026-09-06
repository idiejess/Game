# Decision Log — Halfway Lock

Entries are chronological. Each records the decision, alternatives considered, and the reason.

---

## D-001 — Concept selection (Phase 1)

Five original concepts were generated and scored 1–5 on nine criteria
(originality, player fantasy, 1,000-decision capacity, recurring conflict, character potential,
mystery potential, visual distinctiveness, commercial clarity, technical feasibility).

| # | Concept | Orig | Fantasy | 1000 | Conflict | Chars | Mystery | Visual | Commercial | Feasible | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | **Halfway Lock** — keeper of the summit lock on a continent-spanning canal that is the only crossing between two rival shores. Every vessel, petitioner and telegram is a card. | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 4 | 5 | **43** |
| B | Night dispatcher of a mountain rescue radio service; you only hear voices. | 5 | 4 | 3 | 3 | 4 | 4 | 3 | 3 | 5 | 34 |
| C | Editor of the last printed newspaper in a slowly flooding city; decisions are what to print. | 4 | 4 | 4 | 4 | 4 | 4 | 3 | 3 | 5 | 35 |
| D | Station master of an orbital tether's midpoint transfer station. | 3 | 4 | 4 | 4 | 3 | 4 | 4 | 4 | 4 | 34 |
| E | Warden of a quarantine island between two nations during a slow epidemic. | 3 | 3 | 4 | 4 | 4 | 3 | 3 | 3 | 5 | 32 |

**Selected: A — Halfway Lock.**

Rationale: a lock keeper literally decides who and what passes, which makes hundreds of
consequential binary decisions the natural job rather than a contrivance. The canal sits between
two rival shores, a chartered company, a locktown and the boat people, so factions disagree for
understandable, structural reasons. Water level, traffic, money, employer and town are five
mutually conflicting pressures with meaningful low *and* high failure states. The setting
(lamplit, telegraph-and-steam, invented continent) is neither medieval royalty nor generic
fantasy, and it supports comedy (cargo disputes, eccentric bargees, bureaucracy) and drama
(refugees, war, flood, a drowned town). The central mystery — where the summit water actually
comes from and why it is falling — is planned backward from three resolutions and is embedded
in the primary resource the player watches every turn.

Concept B was the closest runner-up but strains at 1,000 decisions and lacks strong factions.

## D-002 — Five resources
Water, Traffic, Coffers, Company, Town. Chosen because each pair conflicts: passing more boats
drains Water; inspecting boats lowers Traffic but raises Company; tolls raise Coffers and lower
Town; and so on. Both extremes are dangerous for every resource (see Creative Bible §8–9).
Keeper fatigue is a hidden counter rather than a sixth resource to keep the HUD readable on phones.

## D-003 — Engine and format
Godot 4.7.2 (latest stable at time of work), GDScript, JSON content, JSON Schema validated by
both Python tooling (authoring time) and the GDScript loader (runtime, strict). Godot was not
preinstalled; the install is recorded in `.hoplite/settings.json` setup script.

## D-004 — Turn unit
One card = one "watch" (a shift). Runs are measured in watches; the HUD shows "Watch N".
A season/tide unit was rejected because canals have no tides and a day is too granular for
the narrative pace.

## D-005 — Content authoring approach
Cards are hand-authored in JSON batch files of 20–40 cards, one file per arc or category slice,
so batches can be validated and committed independently. No runtime text generation.
Inventory IDs are reserved first (`tools/build_inventory.py`) and the validator enforces that
the produced set equals the inventory set exactly.

## D-006 — Hidden numbers by default
Ordinary play shows direction arrows (▲/▼, single or double) for previewed resource changes.
The exact-effect accessibility option displays numeric deltas. This keeps mobile readability
while satisfying the clarity requirement.

## D-007 — Save numbers are re-typed on read, not on write
The four reported save failures had one root cause: Godot's `JSON.parse` returns every number as
`float`, and the load-time sanitizers compare `typeof()` against integer defaults, discarding
`watch`, `seed`, `rng_state`, `run_number` and `resources`. Alternatives: (a) loosen the sanitizers
to accept floats everywhere, (b) store numbers as strings, (c) coerce whole-valued floats back to
ints once in `SaveManager._read`. Chosen (c): one place, keeps the strict typing that protects
against corrupt saves, changes no on-disk format, and old saves load unchanged.

## D-008 — Branch and remote
The imported repository had no `main` branch on the remote (only the import branch
`hoplite/aitna-17a46edb`). Work proceeds on the thread branch `hoplite/phleious-16c2ad27` and the
draft PR targets the repository's configured base branch. No history is rewritten.
