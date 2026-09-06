# Narrative Bible — Halfway Lock

Machine-readable graph: `content/STORY_GRAPH.json`. This document is the human explanation.

## 1. The mystery, planned backward

**Resolution**: The Summit Pound is fed by the Marrow Cut, a secret tunnel diverting the River Quell, which dried Lowmere and created the Hullfolk. The Cut is failing. The Company has known since Y31. Ansel Dray died in it.

**What must be true for the resolution to be fair**
1. Water visibly falls every watch from watch 1. (Mechanical clue.)
2. Reservoir reports never account for the level (Quenn's cards, MA05).
3. The aqueduct is visibly dry in summer but the pound holds (evergreen weather cards).
4. The brewery well tastes of iron and rises with the pound (Ilse cards, MA08).
5. The Hullfolk song names "the river that went into the hill" (Petronel, MA06).
6. The chapel's founding charter thanks Marrow for "the water I have given" (Hale, MA08).
7. The sluice house is guarded harder than a disused valve deserves (Vosk, MA03).
8. Dray's ledger is in cipher and the cipher key is the sill gauge markings (MA02).
9. Crane's private water counts match Quenn's (MA04/MA09).
10. Old Tobin's Dry Year story mentions "dredging" crews who came at night with no dredgers (Tobin cards).

**Reinterpretation**: the Hullfolk, introduced as smugglers and mooring nuisances, are revealed as the owners of the water; the "vagrants" are the valley's people. Bram's "water debt" changes meaning from a mooring-fee dispute to a literal debt. Pell's beloved canal is the instrument of dispossession. Vosk's harassment becomes protection of the peace.

## 2. Ending taxonomy (50 cards in `endings_meta`)

### Resource deaths (10 cards, 2 per resource) — `end_res_*`
Each edge failure has a plain and a variant ending depending on state (e.g. the Breach kills more if Town is low because nobody helped sandbag).

### Ordinary successes (6) — `end_ord_*`
Surviving to watch 100 with no true route: "The Long Watch" (retire), "Transferred" (Company promotes you sideways), "The Jubilee" (if MA01 complete), "Town's Keeper" (Town high), "Company's Keeper" (Company high), "Quiet Marriage" (relationship route with Ilse/Solas/Quenn implied, Teen-appropriate).

### False endings (6) — `end_false_*`
Conclusions that feel like solving the mystery but are not:
- **The Promotion** (Company 100 with `unlock_vosk_file`): you become the face of the lie.
- **The Drought Report**: you publish Quenn's survey without the Cut; Company blames drought; nothing changes.
- **Dray's Killer**: you accuse Vosk of murder; she is removed; the Cut is still failing.
- **The Sorrel Purchase**: Vane's consortium buys the canal; the water still falls.
- **The Clearance**: Pell's order succeeds; the Hullfolk leave; the Song leaves with them.
- **The Dry Blessing**: Hale's vigil "saves" the water (a wet season); belief deepens.

### Failures with revelations (10) — `end_rev_*`
Deaths or dismissals that unlock a Ledger fact: drowning in the sluice house (unlocks `dray_fate`), dismissed after reading the survey (unlocks `quenn_survey`), etc. These make losing productive.

### Crisis endings (5) — `end_crisis_*`
The Pile-Up, the Fire at the Boatyard, the Riot, the Frost Closure with starvation, the Inquiry.

### Cross-run meta cards (10) — `meta_*`
Ledger reflections at run start (run 2+), Keeper's-chair cards, "the town remembers" cards, and the three true-route gate cards.

### True endings (3) — `end_true_*`
All require: `unlock_cut_map` (or Bram's guidance) AND at least two of `unlock_quenn_survey`, `unlock_lowmere_song`, `unlock_marrow_letters`, AND survive MA12 (Last Water).

- **TE1 — The River Returned** (Hullfolk route): with Bram, Wren and Solas, you open the regulating sluice and return most of the Quell to Lowmere. The canal shrinks to a seasonal road; the Hullfolk go home; Halfway dwindles; you are remembered by the Reed Reach. Requires Town ≥ 40 and Hullfolk faction ≥ 60.
- **TE2 — The Open Ledger** (Truth route): with Crane, Quenn and Hesse (and Vosk if turned), you publish everything under the Compact; both shores take the canal from the Company and fund a real reservoir. Requires Company ≤ 60 (they cannot bury it) and Crane ≥ 60.
- **TE3 — The Keeper's Cut** (Stewardship route): with Vosk, Hale and Tamm, you secretly rebuild Marrow's sluice, sharing water between pound and valley, and keep the secret with a smaller lie. Requires Vosk ≥ 60, Hale ≥ 50, Coffers ≥ 60. The "quietest" ending; the Ledger records that you chose to be the next Vosk.

Each true ending unlocks a distinct Ledger epilogue and the "New Keeper" opening variant.

## 3. Major arcs (12 × 15 cards = 180)

| ID | Title | Owner chars | Entry | Stages (cards) | Interacts with |
|---|---|---|---|---|---|
| MA01 | The Jubilee | Pell, Quenn, Kell | watch ≥ 10, Company ≥ 40 | Plan(3) → Budget(3) → Rehearsal(3) → Ceremony(3) → Aftermath(3) | MA04 throughput demands; MA05 survey can wreck it; MA08 flood |
| MA02 | The Study | Mirren, Fennick, Tobin | Mirren ≥ 30 or `flag_found_ledger` | Locked drawer(3) → Cipher(3) → Gauge(3) → Wire copy(3) → Key(3) | Unlocks `drays_key`; feeds MA11 |
| MA03 | The Auditor's Interest | Vosk, Fennick | watch ≥ 15 | Inspection(3) → Questions(3) → The Sluice House(3) → Offer(3) → Verdict(3) | Suspicion counter; gates MA09; TE3 |
| MA04 | Throughput | Pell, Vane, Crane | Traffic ≤ 35 or ≥ 65 | Record(3) → Corners(3) → Inspectors(3) → Night passages(3) → Reckoning(3) | Pile-Up crisis; Compact; MA07 |
| MA05 | The Reservoir Sums | Quenn, Crane, Vosk | Quenn ≥ 40 & Water ≤ 45 | Drawer(3) → Aqueduct walk(3) → Crane's figures(3) → Drought or Cut(3) → Publish or burn(3) | `quenn_survey`; false ending Drought Report; TE2 |
| MA06 | The Water Debt | Bram, Wren, Petronel, Ilse | Hullfolk ≥ 40 or `flag_honored_remembered` | Mooring(3) → The remembered(3) → The Song(3) → The outfall(3) → The debt named(3) | `lowmere_song`; MA10 opposes; TE1 |
| MA07 | The Rifle Road | Wren, Solas, Vane, Crane | `flag_reeds_cargo` or Sorrel ≥ 55 | Crate(3) → Buyer(3) → Compact seals(3) → Convoy(3) → Choice(3) | Sorrel coup flag; Solas loyalty; MA10 |
| MA08 | High Water | Ilse, Hale, Stroud, Cole | Water ≥ 62 | Cellars(3) → Undercroft(3) → The well(3) → The letters(3) → The charter(3) | `marrow_letters`; Breach crisis; TE3 |
| MA09 | The Vosk File | Vosk, Fennick, Hesse, Crane | Suspicion ≥ 5 & (Fennick ≥ 50 or Hesse ≥ 50) | Rumor(3) → The copy(3) → Leverage(3) → Press(3) → File(3) | `vosk_file`; The Promotion; TE2 |
| MA10 | The Clearance | Pell, Bram, Solas, Ilse | Town ≤ 40 & Hullfolk ≤ 40, or run ≥ 2 & Pell ≥ 60 | Draft(3) → Moot(3) → Order(3) → The Reach(3) → Aftermath(3) | Riot crisis; kills MA06 if completed; false ending |
| MA11 | Into the Cut | Mirren, Bram, Tamm, Hale | `unlock_drays_key` & (Mirren ≥ 50 or Bram ≥ 50) | Door(3) → Descent(3) → What is found(3) → Return(3) → Telling Mirren(3) | `dray_fate`, `cut_map`; drowning revelation ending |
| MA12 | Last Water | all | any true-route prerequisites & watch ≥ 60 | Allies(3) → Plan(3) → The night(3) → The sluice(3) → Dawn(3) | Leads to TE1/2/3 based on ally set |

Each stage has 3 cards; stage cards chain by forced or delayed follow-up, and the arc can be interrupted (a crisis card) and resumed because arc state is stored as `arc_stage` counters.

## 4. Minor arcs (30 × 6 cards = 180)

| ID | Title | Chars | Hook | Outcome flags |
|---|---|---|---|---|
| mi01 | The Geese | src_gate, Ilse | A barge of geese escapes in the chamber. | `geese_loose`, comic callbacks |
| mi02 | The Duel of Precedence | Crane, Vane | Two vessels claim first passage; a formal duel is proposed. | Compact standing |
| mi03 | Iron Spring | Ilse, Stroud | The ale is making people ill; the well. | clue 4 |
| mi04 | The Blessing of Coal | Hale, Vane | A coal fleet demands the blessing rite for its crews. | Concordance/Sorrel |
| mi05 | Dace's Three Things | Dace | The hands present grievances in threes. | strike flag, Town |
| mi06 | The Loan | Cole | Coffers rescue at interest; the interest compounds. | `cole_debt` counter |
| mi07 | The Courier's Headline | Hesse | Hesse wants a story; you are the story. | press standing |
| mi08 | Tobin's Dry Year | Tobin | Old Tobin tells the Dry Year in pieces. | clue 10 |
| mi09 | The Pilgrims | Hale, src_stranger | Concordance pilgrims want free passage to the Lamp Vigil. | Water/Town |
| mi10 | The Drover | src_stranger, Crane | A cattle drover wants to swim the herd through the pound. | Water, comic |
| mi11 | The Runaway | Mirren, Solas | A Sorrel conscript deserts into Halfway. | Solas relationship |
| mi12 | Fever Boat | Stroud, Vosk | A boat with fever aboard; quarantine or pass. | Town/Traffic |
| mi13 | The Telegram Habit | Fennick | Fennick has been reading your wires. | Fennick trust |
| mi14 | The Scrip Riot | Ilse, Pell | Company scrip refused at the inn. | Coffers/Town |
| mi15 | Wren's Favor | Wren | A small favor, then a larger one. | `flag_reeds_cargo` |
| mi16 | The Frost | src_weather, Dace | Ice closes the west; boats trapped in the pound. | Traffic crisis lead-in |
| mi17 | The Lamp Vigil | Hale, Bram | Low-water rite; the Hullfolk hold their own. | clue 5 lead-in |
| mi18 | Tamm's Hull | Tamm, Wren | A hull with a false bottom in the yard. | evidence |
| mi19 | The Rent | Cole, Ilse | Cole raises the town's rents; the moot asks you to intervene. | Town/Coffers |
| mi20 | The Commissioner's Visit | Kell, Pell | Kell arrives unannounced. | Company swings |
| mi21 | The Refugees | src_stranger, Hale, Crane | Families from Sorrel's coalfield strikes at the gate. | Ethics, Town |
| mi22 | The Wager | Vane, Crane | A bet on the water level. | comic, clue 9 |
| mi23 | The Missing Windlass | Mirren, Dace | Theft in the lock house; accusations. | Town/Hullfolk |
| mi24 | The Night Boat | src_gate, Solas | A boat asks passage at night without lights. | MA07 lead-in |
| mi25 | Quenn's Budget | Quenn, Pell | Repairs or the Jubilee bunting. | Coffers |
| mi26 | Petronel's Fiddle | Petronel, Wren | The fiddle is impounded for unpaid mooring. | Song lead-in |
| mi27 | The Surveyor | src_stranger, Vosk | A stranger surveying the north bank; Vosk wants him gone. | Suspicion |
| mi28 | The Keeper's Chair | src_ledger, Mirren | Living in Dray's house. | Mirren |
| mi29 | Hesse's Exposure | Hesse, Fennick | Hesse prints something about you. | press |
| mi30 | The Boundary Stone | Ilse, Dace | The town rehearses running out a Keeper. | Town warning |

## 5. Interaction rules
- Completing MA10 (Clearance) sets `flag_hullfolk_cleared`, which blocks MA06 stages ≥ 3 and TE1.
- MA05 "Publish" with no Cut evidence produces the Drought Report false ending; with `unlock_marrow_letters` it advances TE2.
- MA07 convoy choice sets `flag_sorrel_armed`; in MA12 an armed Sorrel means Solas may refuse TE1.
- High Water (MA08) can trigger the Breach if the player ignores cellars for three cards.
- Minor arcs feed flags used as major-arc entry hints (mi15 → MA07, mi17 → MA06, mi08 → MA05).

## 6. Clue accounting
Ten planted clues, each present in at least two cards, at least six of which are reachable without any unlock. The validator checks `clue_*` flags are set by ≥ 2 cards each.
