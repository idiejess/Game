# Content Report — Halfway Lock

Generated 2026-09-07 00:34 by `tools/generate_reports.py --content`.

## Totals
- **Cards: 1000** (target 1000: OK)
- Validation errors: 0; warnings: 0
- Dialogue analyzer errors: 0; warnings: 562
- Characters: 20 (12 major, 8 supporting) + 5 sources
- Arcs: 12 major, 30 minor; endings: 40; true routes: 3

## Allocation
| Category | Count | Target |
|---|---|---|
| onboarding | 30 | 30 |
| evergreen | 220 | 220 |
| resources | 150 | 150 |
| relationships | 120 | 120 |
| minor_arcs | 180 | 180 |
| major_arcs | 180 | 180 |
| crises | 70 | 70 |
| endings_meta | 50 | 50 |

## Pools
| Pool | Cards |
|---|---|
| character | 13 |
| crisis | 69 |
| ending | 40 |
| fallback | 4 |
| forced | 12 |
| general | 862 |

## Resource-reactive cards per resource
| Resource | Cards |
|---|---|
| coffers | 30 |
| company | 30 |
| town | 30 |
| traffic | 30 |
| water | 30 |

## Relationship cards per major character
| Character | Cards |
|---|---|
| bram | 10 |
| crane | 10 |
| fennick | 10 |
| hale | 10 |
| ilse | 10 |
| mirren | 10 |
| pell | 10 |
| quenn | 10 |
| solas | 10 |
| vane | 10 |
| vosk | 10 |
| wren | 10 |

## Speaker distribution (all cards)
| Speaker | Cards |
|---|---|
| ilse | 79 |
| vosk | 70 |
| pell | 68 |
| crane | 60 |
| quenn | 58 |
| bram | 51 |
| dace | 50 |
| hale | 49 |
| vane | 47 |
| src_ledger | 47 |
| src_gate | 46 |
| solas | 41 |
| mirren | 39 |
| wren | 35 |
| fennick | 33 |
| src_stranger | 32 |
| cole | 31 |
| hesse | 31 |
| stroud | 28 |
| src_weather | 24 |
| src_telegram | 19 |
| tamm | 19 |
| kell | 18 |
| tobin | 14 |
| petronel | 11 |

## Style-guide ratios
- Tradeoff ratio (ordinary cards): **69.7%** (target ≥ 70%)
- Purely positive/negative (ordinary): **9.4%** (target ≤ 20%)
- Cards with delayed/followup/subdeck effects: **3.5%** (target ≥ 25% including flag resolution; see note)
- State-reactive cards (have conditions): **93.7%** (target ≥ 30%)
- Situation length: min 14, mean 36.6, max 49 words

Note on delayed consequences: the `delayed_ratio` counts only explicit `delayed`/`followup`/`subdeck` effects. Delayed consequences in this library are mostly carried by flags and counters (a choice sets `reeds_cargo`, a later card requires it). Counting cards that either set a flag consumed elsewhere or require a flag set elsewhere gives the figure below.
- Cards that create or resolve a flag-carried consequence (excluding `met_*`): **57.8%**

## Clue coverage (cards that set each clue flag)
| Clue | Setters |
|---|---|
| clue_charter | 17 |
| clue_cipher | 17 |
| clue_crane_counts | 11 |
| clue_dry_aqueduct | 6 |
| clue_iron_well | 12 |
| clue_night_dredgers | 12 |
| clue_reservoirs | 22 |
| clue_sluice_guard | 31 |
| clue_song | 22 |
| noticed_water_fall | 12 |

## Unlock sources (cards granting each unlock)
| Unlock | Cards |
|---|---|
| unlock_cut_map | 2 |
| unlock_dray_fate | 2 |
| unlock_drays_key | 3 |
| unlock_lowmere_song | 2 |
| unlock_marrow_letters | 2 |
| unlock_quenn_courage | 1 |
| unlock_quenn_survey | 4 |
| unlock_vosk_file | 5 |

## Analyzer warnings (top 30)
- [cri_money_01] situation 41 words (6-40)
- [cri_money_03] situation 46 words (6-40)
- [cri_money_04] situation 45 words (6-40)
- [cri_money_05] situation 47 words (6-40)
- [cri_company_01] right outcome 26 words (>24)
- [cri_company_02] situation 43 words (6-40)
- [cri_company_03] situation 48 words (6-40)
- [cri_company_03] right outcome 25 words (>24)
- [cri_company_04] situation 46 words (6-40)
- [cri_company_05] left outcome 26 words (>24)
- [cri_company_06] situation 41 words (6-40)
- [cri_town_01] situation 42 words (6-40)
- [cri_town_02] situation 42 words (6-40)
- [cri_town_04] situation 47 words (6-40)
- [cri_town_05] situation 45 words (6-40)
- [cri_town_06] situation 45 words (6-40)
- [cri_town_07] left outcome 33 words (>24)
- [cri_town_08] situation 43 words (6-40)
- [cri_fire_01] situation 45 words (6-40)
- [cri_fire_02] situation 41 words (6-40)
- [cri_fire_03] situation 42 words (6-40)
- [cri_fire_04] situation 43 words (6-40)
- [cri_fire_05] situation 41 words (6-40)
- [cri_frost_01] situation 46 words (6-40)
- [cri_frost_02] situation 42 words (6-40)
- [cri_frost_03] situation 48 words (6-40)
- [cri_frost_04] situation 44 words (6-40)
- [cri_frost_05] situation 45 words (6-40)
- [cri_fever_01] situation 41 words (6-40)
- [cri_fever_02] situation 44 words (6-40)

## Unused registry entries
- Flags: dray_accused_vosk, jubilee_funded, p_jailed_wren, p_prev_keeper_dismissed, p_told_mirren, p_true_ending_seen, promised_ilse, sorrel_purchase_backed
- Counters: ledger_days, p_company_trust, p_hullfolk_honor, p_keepers_lost
