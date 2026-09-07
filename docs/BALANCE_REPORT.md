# Balance Report — Halfway Lock

Generated 2026-09-07 00:34 from `reports/simulations/simulation.json` (9997 runs, 615.1s, 13 strategies).

## Assessment against design targets
| Metric | Value | Target | Status |
|---|---|---|---|
| Runs 40–119 watches | 82% | majority | OK |
| Median run length | 50 | 40–120 | OK |
| Water-edge deaths (all strategies) | 62% | dominant but < 70% | OK |
| Keeper strategy reaches watch 100 | 43% | ≥ 30% | OK |
| Distinct endings reached | 25 / 40 | ≥ 20 in 10k scripted runs | OK |
| Revelation endings | 5.7% | 1–10% | OK |
| True endings | 0.16% | rare (0.05–2%) | OK |
| Major arcs completed at least once | 10 / 12 | 12 / 12 | ATTENTION |
| Stalls | 0 | 0 | OK |
| Fallback-card runs | 1 | < 1% | OK |
| Unseen cards | 67 | informational | OK |

Notes: strategies are scripted policies, not players; they never read clue text, so mystery endings and arc completions are lower bounds. Unseen cards are almost all late arc beats or resource cards gated on states (very high Town, very low Coffers, sustained Water ≥ 62) that scripted play rarely sustains; they are reachable by construction (see `reports/content/arc_audit.json`). Rows marked ATTENTION are tracked in `docs/REMAINING_WORK.md`.

## Run length
- Mean: **59.16** watches; median: **50**

| Watches | Runs |
|---|---|
| 20-29 | 73 |
| 30-39 | 1642 |
| 40-49 | 2709 |
| 50-59 | 2504 |
| 60-69 | 453 |
| 70-79 | 364 |
| 80-89 | 319 |
| 90-99 | 259 |
| 100-109 | 1609 |
| 110-119 | 9 |
| 120-129 | 9 |
| 130-139 | 8 |
| 140-149 | 9 |
| 150-159 | 3 |
| 160-169 | 27 |

## Endings
| Ending | Runs | Share |
|---|---|---|
| end_res_water_min | 6217 | 62.2% |
| end_ord_long_watch | 998 | 10.0% |
| end_res_company_max | 512 | 5.1% |
| end_res_town_max | 478 | 4.8% |
| end_false_blessing | 452 | 4.5% |
| end_rev_tobin | 400 | 4.0% |
| end_crisis_fever | 294 | 2.9% |
| end_ord_jubilee | 124 | 1.2% |
| end_crisis_frost | 107 | 1.1% |
| end_rev_cipher | 99 | 1.0% |
| end_false_hero | 78 | 0.8% |
| end_rev_sluice | 68 | 0.7% |
| end_ord_towns_keeper | 49 | 0.5% |
| end_false_drought | 21 | 0.2% |
| end_ord_companys_keeper | 17 | 0.2% |
| end_false_purchase | 15 | 0.2% |
| end_res_traffic_min | 14 | 0.1% |
| end_res_water_max | 13 | 0.1% |
| end_true_river | 12 | 0.1% |
| end_false_killer | 10 | 0.1% |
| end_ord_quiet | 7 | 0.1% |
| end_crisis_inquiry | 5 | 0.1% |
| end_true_ledger | 4 | 0.0% |
| end_res_coffers_min | 2 | 0.0% |
| end_rev_letters | 1 | 0.0% |

## Deaths by resource edge
| Resource | Runs | Share of deaths |
|---|---|---|
| coffers | 2 | 0.0% |
| company | 512 | 7.1% |
| town | 478 | 6.6% |
| traffic | 14 | 0.2% |
| water | 6230 | 86.1% |

## True endings reached: {'end_true_ledger': 4, 'end_true_river': 12}

## Stalls (no eligible card and no fallback): **0**
## Fallback-card runs: **1** (9 draws)
## Selection sources: {'forced': 29980, 'weighted': 567013, 'delayed': 4481, 'fallback': 9}

## Unseen cards across all runs: **67**
- cri_company_01
- cri_company_02
- cri_company_05
- cri_money_06
- cri_pileup_02
- cri_pileup_04
- cri_pileup_06
- cri_town_01
- cri_town_02
- cri_town_03
- cri_town_04
- cri_town_05
- cri_town_06
- cri_town_08
- ma05_15
- ma06_14
- ma06_15
- ma07_12
- ma07_15
- ma08_06
- ma08_07
- ma08_08
- ma08_09
- ma08_10
- ma08_11
- ma08_12
- ma08_13
- ma08_14
- ma08_15
- ma09_15
- ma10_15
- ma11_15
- ma12_12
- ma12_15
- mi23_6
- mi30_2
- mi30_3
- mi30_4
- mi30_5
- mi30_6
- rel_hale_08
- rel_solas_08
- res_coffers_17
- res_coffers_19
- res_coffers_20
- res_coffers_25
- res_coffers_26
- res_coffers_28
- res_coffers_29
- res_coffers_30
- res_company_05
- res_company_10
- res_company_11
- res_company_12
- res_town_01
- res_town_02
- res_town_03
- res_town_04
- res_town_05
- res_town_07
- res_town_08
- res_town_09
- res_town_11
- res_town_12
- res_town_13
- res_town_14
- res_town_15

## Rare cards (< 0.5% of runs): **232**
- cri_company_03
- cri_company_04
- cri_fire_04
- cri_flood_01
- cri_flood_02
- cri_flood_03
- cri_flood_04
- cri_flood_05
- cri_flood_06
- cri_flood_07
- cri_flood_08
- cri_frost_04
- cri_money_01
- cri_money_02
- cri_money_03
- cri_money_04
- cri_money_05
- cri_pileup_01
- cri_pileup_03
- cri_pileup_05
- cri_recover_03
- cri_recover_04
- end_crisis_inquiry
- end_false_drought
- end_false_killer
- end_false_purchase
- end_ord_companys_keeper
- end_ord_quiet
- end_ord_towns_keeper
- end_res_coffers_min
- end_res_traffic_min
- end_res_water_max
- end_rev_letters
- end_true_ledger
- end_true_river
- evg_cargo_06
- evg_chapel_03
- evg_chapel_14
- evg_company_orders_14
- evg_order_06

## Most frequent cards
| Card | Appearances |
|---|---|
| onb_01 | 9997 |
| meta_new_keeper_2 | 8736 |
| end_res_water_min | 6217 |
| mi10_1 | 5040 |
| meta_ledger_cipher | 4449 |
| cri_dry_06 | 4403 |
| res_water_01 | 4386 |
| ma01_01 | 4272 |
| ma10_01 | 4135 |
| ma04_01 | 4063 |
| mi01_1 | 3792 |
| mi01_2 | 3668 |
| evg_weather_06 | 3578 |
| evg_weather_11 | 3575 |
| evg_weather_20 | 3534 |

## Arc entry / completion rate
| Arc | Entered | Completed |
|---|---|---|
| MA01 | 43.0% | 0.3% |
| MA02 | 12.8% | 0.3% |
| MA03 | 12.2% | 3.7% |
| MA04 | 40.6% | 1.2% |
| MA05 | 20.3% | 1.3% |
| MA06 | 18.8% | 0.6% |
| MA07 | 6.2% | 0.1% |
| MA08 | 0.5% | 0.0% |
| MA09 | 7.6% | 0.1% |
| MA10 | 41.4% | 0.1% |
| MA11 | 1.9% | 0.2% |
| MA12 | 1.3% | 0.0% |
| mi01 | 37.9% | 8.9% |
| mi02 | 2.9% | 1.8% |
| mi03 | 6.6% | 0.3% |
| mi04 | 2.7% | 0.4% |
| mi05 | 12.0% | 1.2% |
| mi06 | 2.2% | 0.1% |
| mi07 | 32.5% | 1.6% |
| mi08 | 9.8% | 0.2% |
| mi09 | 14.3% | 0.6% |
| mi10 | 50.4% | 41.6% |
| mi11 | 3.1% | 0.5% |
| mi12 | 30.9% | 2.5% |
| mi13 | 13.4% | 0.5% |
| mi14 | 3.3% | 0.0% |
| mi15 | 9.2% | 0.1% |
| mi16 | 24.1% | 0.0% |
| mi17 | 12.4% | 0.6% |
| mi18 | 5.8% | 0.0% |
| mi19 | 1.8% | 0.2% |
| mi20 | 20.7% | 1.0% |
| mi21 | 34.6% | 0.1% |
| mi22 | 3.8% | 0.4% |
| mi23 | 0.9% | 0.0% |
| mi24 | 12.2% | 0.8% |
| mi25 | 12.0% | 0.1% |
| mi26 | 10.8% | 0.2% |
| mi27 | 28.7% | 0.4% |
| mi28 | 34.8% | 1.5% |
| mi29 | 5.8% | 0.1% |
| mi30 | 0.0% | 0.0% |

## Character appearance rate (share of runs)
| Speaker | Rate |
|---|---|
| pell | 100.0% |
| src_gate | 99.8% |
| src_weather | 99.5% |
| src_stranger | 97.8% |
| src_ledger | 96.9% |
| src_telegram | 88.4% |
| hesse | 58.4% |
| ilse | 55.7% |
| dace | 49.9% |
| bram | 38.9% |
| fennick | 37.3% |
| kell | 36.2% |
| tobin | 35.7% |
| tamm | 34.7% |
| solas | 33.2% |
| quenn | 32.1% |
| vosk | 31.3% |
| petronel | 30.6% |
| vane | 30.0% |
| crane | 29.4% |
| hale | 29.4% |
| mirren | 29.2% |
| stroud | 28.8% |
| wren | 27.7% |
| cole | 14.5% |

## Unlock rate (share of runs with unlock in profile)
| Unlock | Rate |
|---|---|
| unlock_cut_map | 5.5% |
| unlock_dray_fate | 2.5% |
| unlock_drays_key | 8.8% |
| unlock_lowmere_song | 2.8% |
| unlock_marrow_letters | 0.1% |
| unlock_quenn_courage | 0.9% |
| unlock_quenn_survey | 4.2% |
| unlock_true_ledger | 0.1% |
| unlock_true_river | 0.4% |
| unlock_vosk_file | 0.2% |

## Per strategy
| Strategy | Runs | Mean length | Top endings |
|---|---|---|---|
| random | 769 | 61.2 | end_res_water_min 458, end_res_town_max 70, end_ord_long_watch 33 |
| balance | 769 | 59.1 | end_res_water_min 553, end_ord_long_watch 76, end_false_blessing 53 |
| keeper | 769 | 89.2 | end_ord_long_watch 327, end_res_water_min 123, end_rev_tobin 98 |
| risk_seek | 769 | 60.0 | end_res_town_max 371, end_res_water_min 185, end_crisis_frost 79 |
| risk_avoid | 769 | 58.9 | end_res_water_min 596, end_ord_long_watch 75, end_false_blessing 37 |
| loyalist:vosk | 769 | 60.8 | end_res_water_min 556, end_ord_long_watch 83, end_false_blessing 48 |
| loyalist:bram | 769 | 60.3 | end_res_water_min 562, end_ord_long_watch 88, end_false_blessing 35 |
| loyalist:mirren | 769 | 65.0 | end_res_water_min 500, end_ord_long_watch 119, end_rev_tobin 49 |
| faction:company | 769 | 41.4 | end_res_company_max 433, end_res_water_min 303, end_false_hero 18 |
| faction:hullfolk | 769 | 59.4 | end_res_water_min 567, end_ord_long_watch 82, end_false_blessing 51 |
| mystery | 769 | 53.7 | end_res_water_min 612, end_ord_long_watch 43, end_false_blessing 42 |
| short_term | 769 | 41.7 | end_res_water_min 646, end_res_company_max 55, end_res_town_max 37 |
| long_term | 769 | 58.5 | end_res_water_min 556, end_ord_long_watch 68, end_false_blessing 37 |
