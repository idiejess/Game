# Card Schema and Authoring Guide

Authoritative schema: `schemas/card.schema.json`. Runtime loader: `game/autoload/ContentDB.gd` (strict; rejects unknown fields, undeclared flags/counters, bad references). Authoring validator: `tools/validate_content.py`; style: `tools/analyze_dialogue.py`.

## File layout
`content/cards/<category>/<batch>.json` → `{"cards": [ card, card, ... ]}`. A card's `category` must equal its directory. Card IDs are reserved in `content/CARD_INVENTORY.json`; never invent IDs outside it (the total is exactly 1,000).

## Minimal card
```json
{"id": "evg_tolls_03", "category": "evergreen", "speaker": "ilse", "expression": "wry",
 "text": "Scrip again. The Company store takes it; my cellar does not. Whose money is the Keeper paid in?",
 "left":  {"label": "Coin, from now on", "outcome": "\"Then you'll eat here.\"", "effects": {"resources": {"coffers": -3, "town": 4}, "relationships": {"ilse": 4}}},
 "right": {"label": "Scrip is the Company's", "outcome": "\"So are you, then.\"", "effects": {"resources": {"company": 3, "town": -3}, "relationships": {"ilse": -3}}},
 "conditions": {"flags_all": ["met_ilse"]}, "cooldown": 15, "tags": ["res:coffers"]}
```

## Fields
| Field | Meaning |
|---|---|
| `id` | inventory ID, `^[a-z][a-z0-9]*(_[a-z0-9]+)+$` |
| `speaker` / `expression` | character id from `content/characters/`; expression must exist for that character |
| `text` | 6–32 words (endings up to 60); one dilemma |
| `text_variants` | `[{"when": conditions, "text": ...}]` first match wins |
| `left`/`right` | `label` (1–8 words), optional `outcome` (≤24 words), `effects` |
| `conditions` | eligibility (see below) |
| `weight` | base weight (default 1); `weight_mods`: `[{"when": cond, "multiply": x}]` |
| `cooldown` | watches before reappearing; `max_per_run` default 1 |
| `pool` | `general` (default) · `character` · `crisis` (only drawn on Ledger Days / danger bands / every 7th watch) · `forced` (only via followup/delayed/subdeck) · `ending` (only via ending trigger) · `fallback` (only when nothing else is eligible) |
| `arc` | `{"id": "MA02", "stage": 3}`; arc cards of stage N+1 get ×3 weight while arc is active at stage N |
| `tags` | `res:<resource>` gives ×2.5 weight when that resource is in a danger band (≤30 or ≥70) |
| `sound`, `achievement`, `notes` | optional |

## Effects
`resources` (water/traffic/coffers/company/town, ±), `relationships` (character ±), `factions` (company/town/hullfolk/aldmere/sorrel/concordance ±), `flags_set`/`flags_clear` (declared in FLAG_REGISTRY), `counters`/`counters_set` (declared in COUNTER_REGISTRY), `followup` (card forced next), `delayed` (`[{"card","delay","delay_max"}]`), `delayed_resources` (`[{"delay","resources","message"}]`), `subdeck` (`{"id","cards","shuffle","interleave"}`), `arc` (`{"MA02": {"stage": 2, "status": "active"}}`), `unlocks`, `lore`, `objectives_complete`, `ending` (+`ending_chance`), `shake`, `sound`.

## Conditions
`flags_all/any/none`, `resources/relationships/factions/counters/arc_stage` (`{"min","max"}` ranges), `run`, `watch`, `seen_cards`, `unseen_cards`, `seen_cards_any`, `unlocks`, `unlocks_none`, `arc_status`, `endings_seen/unseen`. Persistent flags/counters begin with `p_`.

## Arcs
Major arcs: 15 cards, 5 stages × 3. Minor arcs: 6 cards, 6 stages × 1. Stage-1 cards carry the entry condition and set `"arc": {"MAxx": {"stage": 1, "status": "active"}}` is **not** needed: the TurnController activates an arc when any of its cards is resolved and advances the stage to the card's stage. Later-stage cards should require `arc_stage: {"MAxx": {"min": N-1}}` (and usually a flag from the previous stage). The final card sets `arc: {"MAxx": {"status": "completed"}}` or `failed`.

## Effect magnitudes
Ordinary cards: ±2 to ±6 per resource; strong cards ±8; crisis and ending cards up to ±15. Relationships ±2 to ±8. Every card must change something; left and right must differ.

## Workflow
1. Write a batch file (20–40 cards).
2. `python3 tools/validate_content.py --partial` → 0 errors.
3. `python3 tools/analyze_dialogue.py --files content/cards/<cat>/<batch>.json` → 0 errors.
4. Commit the batch. `python3 tools/validate_content.py --partial --update-inventory` refreshes inventory statuses.
