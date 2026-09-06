#!/usr/bin/env python3
"""Build content/STORY_GRAPH.json from the arc design tables.

The graph documents every arc's premise, entry, stages, branches, state changes,
outcomes, cross-run effects, cards used, exits and interactions. It is consumed by
tools/validate_content.py (arc/card consistency, reachability) and the in-game
objectives/archive screens.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
INV = json.loads((ROOT / "content" / "CARD_INVENTORY.json").read_text())
OUT = ROOT / "content" / "STORY_GRAPH.json"

cards_by_arc = {}
for c in INV["cards"]:
    if c["arc"]:
        cards_by_arc.setdefault(c["arc"], []).append(c["id"])

MAJOR = {
    "MA01": dict(title="The Jubilee", premise="Pell wants the canal's eightieth year celebrated at the summit with a record day of traffic and a visit from Commissioner Kell; the budget, the water and the truth all get in the way.",
                 characters=["pell", "quenn", "kell", "ilse"],
                 entry={"watch": {"min": 10}, "resources": {"company": {"min": 40}}, "flags_none": ["jubilee_ruined"]},
                 stages=["Plan: Pell announces; Keeper decides scale", "Budget: bunting vs repairs; Cole's loan tempts", "Rehearsal: throughput demands strain Water", "Ceremony: Kell arrives; a public moment", "Aftermath: credit, blame, or a quiet ruin"],
                 branches=["Fund it (coffers-) or refuse (pell-)", "Repairs first sets budget_repairs and lowers jubilee_progress", "Ceremony during high water risks flood; during survey publication ruins it"],
                 state=["jubilee_planned", "jubilee_funded", "jubilee_held", "jubilee_ruined", "kell_present", "counter jubilee_progress"],
                 success="jubilee_held with company+, town+; enables end_ord_jubilee.",
                 failure="jubilee_ruined: company-, pell relationship-, Hesse prints it.",
                 delayed="Kell remembers the Keeper (mi20, end cards). Traffic strain feeds MA04.",
                 cross_run="p_company_trust rises on success.",
                 exit="Stage 5 card resolves the arc as completed or failed.",
                 interactions=["MA04", "MA05", "MA08", "mi20", "mi25"]),
    "MA02": dict(title="The Study", premise="Dray's locked study holds a ciphered ledger; Mirren, Fennick and Tobin each hold a piece of the key.",
                 characters=["mirren", "fennick", "tobin"],
                 entry={"flags_any": ["found_ledger"], "relationships": {"mirren": {"min": 30}}},
                 stages=["Locked drawer: open it, or wait for Mirren", "Cipher: Mirren admits she has it", "Gauge: the sill markings are the key", "Wire copy: Fennick's kept telegram", "Key: a brass key stamped S.H."],
                 branches=["Force the drawer (mirren-) or earn it", "Share the cipher with Mirren or work alone", "Take the key to the sluice house or give it to Vosk"],
                 state=["found_ledger", "cipher_solved", "has_wire_copy", "clue_cipher", "counter cipher_progress", "unlock_drays_key"],
                 success="unlock_drays_key granted; MA11 entry opens.",
                 failure="Vosk takes the ledger: suspicion+, arc failed, but cipher_progress persists via Ledger.",
                 delayed="Fennick's wire copy arrives 5-12 watches after asking.",
                 cross_run="p_cipher_progress carries partial decoding between runs.",
                 exit="Stage 5 resolves.",
                 interactions=["MA03", "MA11", "mi13", "mi28", "mi08"]),
    "MA03": dict(title="The Auditor's Interest", premise="Vosk inspects the Keeper more closely than the accounts deserve, and her interest sharpens around the sluice house.",
                 characters=["vosk", "fennick"],
                 entry={"watch": {"min": 15}},
                 stages=["Inspection: the toll book under her eye", "Questions: what the Keeper has noticed", "The Sluice House: a locked door on the north bank", "Offer: silence for protection", "Verdict: ally, enemy or nothing"],
                 branches=["Answer honestly (suspicion+) or evade", "Go to the sluice house (clue_sluice_guard) or leave it", "Accept the offer (vosk_ally, TE3 path) or refuse (vosk_enemy)"],
                 state=["met_vosk", "suspicion", "sluice_house_seen", "clue_sluice_guard", "vosk_ally", "vosk_enemy", "suspicion_high"],
                 success="vosk_ally; Vosk protects during audits.",
                 failure="vosk_enemy; audit_pending; MA09 becomes hostile.",
                 delayed="An audit arrives 10-20 watches after a hostile verdict.",
                 cross_run="Vosk recalls previous Keepers' answers (meta_vosk_remembers).",
                 exit="Stage 5 resolves.",
                 interactions=["MA02", "MA09", "MA12", "mi27", "mi13"]),
    "MA04": dict(title="Throughput", premise="Pell's record attempt and Vane's contracts push the gate to cut corners, while Crane counts every breach of the Compact.",
                 characters=["pell", "vane", "crane", "solas"],
                 entry={"resources": {"traffic": {"max": 35}}},
                 entry_alt={"resources": {"traffic": {"min": 65}}},
                 stages=["Record: the target is set", "Corners: waive inspections", "Inspectors: Crane objects formally", "Night passages: unlit boats", "Reckoning: a near miss or a collision"],
                 branches=["Waive inspections (inspections_waived) or refuse", "Allow night passages (night_passages) or not", "Reckoning: collision leads to cri_pileup; refusal ends record"],
                 state=["throughput_record", "inspections_waived", "night_passages", "compact_breached", "chamber_collision"],
                 success="Record set: company+, traffic high; Crane's report hostile.",
                 failure="chamber_collision -> crisis pool; inquiry.",
                 delayed="Crane files under the Compact; Aldmere wire 8 watches later.",
                 cross_run="none",
                 exit="Stage 5 resolves.",
                 interactions=["MA01", "MA07", "cri_pileup", "mi02", "mi24"]),
    "MA05": dict(title="The Reservoir Sums", premise="Quenn's figures for the Ninefold Reservoirs never account for the pound; Crane has been counting too.",
                 characters=["quenn", "crane", "vosk"],
                 entry={"relationships": {"quenn": {"min": 40}}, "resources": {"water": {"max": 45}}},
                 stages=["Drawer: Quenn admits the survey copy", "Aqueduct walk: the dry channel", "Crane's figures: they match", "Drought or Cut: what the numbers mean", "Publish or burn"],
                 branches=["Read the survey (read_survey, clue_reservoirs) or leave it", "Bring Crane in (clue_crane_counts, crane_recruited)", "Publish without the Cut: end_false_drought; with letters or Cut: TE2 path; burn: survey_burned"],
                 state=["read_survey", "clue_reservoirs", "clue_dry_aqueduct", "clue_crane_counts", "crane_recruited", "survey_published", "survey_burned", "quenn_brave", "quenn_silenced", "unlock_quenn_survey"],
                 success="unlock_quenn_survey; quenn_brave.",
                 failure="quenn_silenced (transferred); suspicion+.",
                 delayed="Vosk reacts 3-6 watches after any publication.",
                 cross_run="p_protected_quenn if Quenn kept safe.",
                 exit="Stage 5 resolves.",
                 interactions=["MA01", "MA09", "MA12", "mi22", "mi25", "mi08"]),
    "MA06": dict(title="The Water Debt", premise="Bram's mooring dispute becomes the story of the Hullfolk's origins as Petronel sings the Lowmere Song verse by verse.",
                 characters=["bram", "wren", "petronel", "ilse"],
                 entry={"factions": {"hullfolk": {"min": 40}}},
                 entry_alt={"flags_all": ["honored_remembered"]},
                 stages=["Mooring: the holding is challenged", "The remembered: an invitation", "The Song: verses", "The outfall: Bram names a place on the north bank", "The debt named"],
                 branches=["Uphold the holding (ilse-, bram+) or the town", "Attend the remembrance (honored_remembered)", "Promise Bram the debt will be named (promised_bram)"],
                 state=["honored_remembered", "clue_song", "song_heard", "counter song_verses", "promised_bram", "unlock_lowmere_song"],
                 success="unlock_lowmere_song; hullfolk faction high; TE1 path.",
                 failure="Blocked by hullfolk_cleared; Bram mourning.",
                 delayed="Hullfolk favors return as help during floods.",
                 cross_run="p_hullfolk_honor; meta_hullfolk_gift.",
                 exit="Stage 5 resolves.",
                 interactions=["MA10", "MA11", "MA12", "mi17", "mi26", "mi15"]),
    "MA07": dict(title="The Rifle Road", premise="Wren's reed cargo is rifles for Sorrel; Solas is the buyer, Vane the paymaster, Crane the law.",
                 characters=["wren", "solas", "vane", "crane"],
                 entry={"flags_any": ["reeds_cargo"]},
                 entry_alt={"factions": {"sorrel": {"min": 55}}},
                 stages=["Crate: what is in the reeds", "Buyer: Solas admits it", "Compact seals: Crane refuses the second seal", "Convoy: the armed boats arrive", "Choice: let them through, stop them, or warn Aldmere"],
                 branches=["Protect Wren (wren_protected) or jail her (wren_jailed)", "One seal (arms_passed, compact_breached) or hold (arms_held)", "sorrel_armed / convoy_stopped / coup_warned"],
                 state=["reeds_cargo", "rifles_known", "wren_protected", "wren_jailed", "arms_held", "arms_passed", "sorrel_armed", "convoy_stopped", "coup_warned", "solas_owed", "solas_refused_order"],
                 success="convoy_stopped or coup_warned with Solas kept: solas_owed.",
                 failure="sorrel_armed: Sorrel faction high, Aldmere hostile; Solas may refuse TE1 in MA12.",
                 delayed="Aldmere wire 10 watches after arms pass; Sorrel news 6 watches after stop.",
                 cross_run="p_jailed_wren.",
                 exit="Stage 5 resolves.",
                 interactions=["MA04", "MA10", "MA12", "mi15", "mi18", "mi24", "mi11"]),
    "MA08": dict(title="High Water", premise="The pound is high; cellars and the chapel undercroft flood, the brewery well rises with it, and the undercroft holds Marrow's letters.",
                 characters=["ilse", "hale", "stroud", "cole"],
                 entry={"resources": {"water": {"min": 62}}},
                 stages=["Cellars: Ilse demands the paddles", "Undercroft: Hale will not let anyone down", "The well: iron and the pound", "The letters: what the water uncovered", "The charter: 'the water I have given'"],
                 branches=["Open paddles full (paddles_opened_full, water-, traffic-) or sandbag (town labor)", "Force the undercroft (hale-) or wait", "Take the letters (letters_taken) or leave them"],
                 state=["cellars_flooded", "undercroft_flooded", "sandbags_ordered", "paddles_opened_full", "clue_iron_well", "well_tested", "read_letters", "letters_taken", "clue_charter", "hale_confessed", "unlock_marrow_letters"],
                 success="unlock_marrow_letters; Hale confessed or reconciled.",
                 failure="flood_ignored 3 -> Breach risk; letters lost to water.",
                 delayed="Ale sickness 4-8 watches after the well is ignored.",
                 cross_run="none",
                 exit="Stage 5 resolves.",
                 interactions=["MA01", "MA12", "mi03", "mi17", "cri_flood"]),
    "MA09": dict(title="The Vosk File", premise="Fennick and Hesse can get at Vosk's Y31 file, which proves the Company has known for fifty years.",
                 characters=["vosk", "fennick", "hesse", "crane"],
                 entry={"counters": {"suspicion": {"min": 5}}, "relationships": {"fennick": {"min": 50}}},
                 entry_alt={"counters": {"suspicion": {"min": 5}}, "relationships": {"hesse": {"min": 50}}},
                 stages=["Rumor", "The copy", "Leverage", "Press", "File"],
                 branches=["Blackmail Vosk (vosk_confronted, vosk_enemy) or bring it to Crane", "Give Hesse the story (hesse_has_story) or hold it", "End: unlock_vosk_file; The Promotion path if Company 100"],
                 state=["vosk_file_seen", "vosk_confronted", "hesse_has_story", "hesse_friendly", "hesse_hostile", "fennick_trusted", "unlock_vosk_file"],
                 success="unlock_vosk_file; Crane witness.",
                 failure="Fennick exposed (fennick_exposed) and dismissed; Vosk enemy.",
                 delayed="Hesse prints 3-5 watches after receiving.",
                 cross_run="none",
                 exit="Stage 5 resolves.",
                 interactions=["MA03", "MA05", "MA12", "mi07", "mi13", "mi29"]),
    "MA10": dict(title="The Clearance", premise="Pell revives the Y44 order to clear the Hullfolk from the Reed Reach; the town is asked to help and Solas is asked to enforce.",
                 characters=["pell", "ilse", "bram", "solas"],
                 entry={"resources": {"town": {"max": 40}}, "factions": {"hullfolk": {"max": 40}}},
                 entry_alt={"run": {"min": 2}, "relationships": {"pell": {"min": 60}}},
                 stages=["Draft", "Moot", "Order", "The Reach", "Aftermath"],
                 branches=["Sign (clearance_signed) or refuse (clearance_refused)", "Ask Solas to enforce: he may refuse (solas_refused_order)", "Riot or departure"],
                 state=["clearance_drafted", "clearance_signed", "clearance_refused", "hullfolk_cleared", "moot_called", "riot_brewing", "solas_refused_order"],
                 success="From Pell's view: hullfolk_cleared -> end_false_clearance available; MA06 blocked.",
                 failure="Riot -> cri_town; or refusal -> company-.",
                 delayed="Riot 2-4 watches after the order.",
                 cross_run="p_clearance_done.",
                 exit="Stage 5 resolves.",
                 interactions=["MA06", "MA07", "MA12", "cri_town", "mi30", "mi05"]),
    "MA11": dict(title="Into the Cut", premise="With Dray's key and Bram's knowledge of the outfall, the Keeper enters the Marrow Cut and finds what Dray found.",
                 characters=["mirren", "bram", "tamm", "hale"],
                 entry={"unlocks": ["unlock_drays_key"], "relationships": {"mirren": {"min": 50}}},
                 entry_alt={"unlocks": ["unlock_drays_key"], "relationships": {"bram": {"min": 50}}},
                 stages=["Door", "Descent", "What is found", "Return", "Telling Mirren"],
                 branches=["Go alone (risk end_rev_sluice) or with Tamm/Bram", "Take Dray's ledger page (cut_mapped)", "Tell Mirren (told_mirren) or keep it (mirren_knows_secret_kept)"],
                 state=["sluice_house_opened", "entered_cut", "knows_cut", "knows_dray_fate", "cut_mapped", "told_mirren", "mirren_knows_secret_kept", "unlock_dray_fate", "unlock_cut_map"],
                 success="unlock_cut_map and unlock_dray_fate.",
                 failure="Drowning: end_rev_sluice (still unlocks dray_fate).",
                 delayed="Mirren's response 3 watches after telling.",
                 cross_run="p_told_mirren.",
                 exit="Stage 5 resolves.",
                 interactions=["MA02", "MA06", "MA12", "mi28"]),
    "MA12": dict(title="Last Water", premise="The Keeper gathers allies and chooses how the truth about the Cut will end: the river returned, the ledger opened, or the cut kept.",
                 characters=["vosk", "bram", "quenn", "hale", "crane", "solas", "wren", "mirren"],
                 entry={"watch": {"min": 60}, "unlocks": ["unlock_cut_map"]},
                 stages=["Allies", "Plan", "The night", "The sluice", "Dawn"],
                 branches=["route_river (Bram, Wren, Solas)", "route_ledger (Crane, Quenn, Hesse)", "route_cut (Vosk, Hale, Tamm)"],
                 state=["allies_gathered", "route_river", "route_ledger", "route_cut", "sluice_rebuilt", "counter allies"],
                 success="end_true_river / end_true_ledger / end_true_cut.",
                 failure="Betrayal or resource edge during the night: crisis endings.",
                 delayed="none; the arc is terminal.",
                 cross_run="p_true_ending_seen; distinct epilogues.",
                 exit="Ends the run.",
                 interactions=["all"]),
}

MINOR = {
    "mi01": ("The Geese", ["ilse", "dace"], {"watch": {"min": 6}}, ["geese_loose", "geese_resolved", "counter geese_count"], "Comic; callbacks in evergreen cards."),
    "mi02": ("The Duel of Precedence", ["crane", "vane", "solas"], {"flags_all": ["met_crane", "met_vane"]}, ["duel_pending"], "Compact standing; feeds MA04."),
    "mi03": ("Iron Spring", ["stroud", "ilse", "quenn"], {"flags_all": ["met_ilse"], "watch": {"min": 12}}, ["ale_sickness", "well_tested", "well_closed", "clue_iron_well"], "Clue 4; feeds MA08."),
    "mi04": ("The Blessing of Coal", ["vane", "hale"], {"flags_all": ["met_hale", "met_vane"]}, [], "Concordance vs Sorrel; comic."),
    "mi05": ("Dace's Three Things", ["dace", "pell", "ilse"], {"flags_all": ["met_dace"]}, ["dace_grievances_heard", "strike", "hands_short"], "Labor; feeds MA10 moot."),
    "mi06": ("The Loan", ["cole", "ilse"], {"resources": {"coffers": {"max": 40}}}, ["cole_loan", "cole_defaulted", "counter cole_debt"], "Coffers rescue at compounding cost."),
    "mi07": ("The Courier's Headline", ["hesse", "fennick", "pell"], {"watch": {"min": 10}}, ["pressed_by_hesse", "hesse_friendly", "hesse_hostile"], "Press standing; feeds MA09."),
    "mi08": ("Tobin's Dry Year", ["tobin", "mirren", "vosk"], {"flags_all": ["met_tobin"]}, ["tobin_story_1", "tobin_story_2", "clue_night_dredgers", "counter tobin_pieces"], "Clue 10; hints MA05."),
    "mi09": ("The Pilgrims", ["hale", "crane"], {"flags_all": ["met_hale"]}, ["pilgrims_passed"], "Water vs Town vs Concordance."),
    "mi10": ("The Drover", ["crane", "dace", "ilse"], {"watch": {"min": 8}}, [], "Comic; Water."),
    "mi11": ("The Runaway", ["mirren", "solas"], {"flags_all": ["met_solas", "met_mirren"]}, ["deserter_hidden", "deserter_returned"], "Solas relationship; feeds MA07."),
    "mi12": ("Fever Boat", ["stroud", "vosk", "ilse"], {"watch": {"min": 14}}, ["fever_aboard", "quarantine"], "Town vs Traffic; feeds cri_fever."),
    "mi13": ("The Telegram Habit", ["fennick", "vosk"], {"flags_all": ["met_fennick"]}, ["fennick_trusted", "fennick_exposed"], "Fennick trust; feeds MA02/MA09."),
    "mi14": ("The Scrip Riot", ["ilse", "pell", "cole", "dace"], {"resources": {"coffers": {"max": 45}}, "flags_all": ["met_ilse"]}, ["scrip_refused"], "Coffers vs Town."),
    "mi15": ("Wren's Favor", ["wren", "bram"], {"flags_all": ["met_wren"]}, ["reeds_cargo", "wren_protected", "counter hullfolk_favors"], "Lead-in to MA07."),
    "mi16": ("The Frost", ["dace", "vane", "quenn", "ilse"], {"watch": {"min": 20}}, ["frost"], "Traffic crisis lead-in; feeds cri_frost."),
    "mi17": ("The Lamp Vigil", ["hale", "bram", "petronel"], {"resources": {"water": {"max": 40}}, "flags_all": ["met_hale"]}, ["lamp_vigil_held", "hullfolk_vigil_joined", "honored_remembered"], "Clue 5 lead-in; feeds MA06."),
    "mi18": ("Tamm's Hull", ["tamm", "wren", "crane"], {"flags_all": ["met_tamm"]}, ["false_bottom_found", "reeds_cargo"], "Evidence; feeds MA07."),
    "mi19": ("The Rent", ["cole", "ilse"], {"flags_all": ["met_cole", "met_ilse"]}, ["rent_intervened"], "Town vs Coffers."),
    "mi20": ("The Commissioner's Visit", ["pell", "kell", "vosk"], {"watch": {"min": 25}}, ["kell_present", "praised_by_board"], "Company swings; feeds MA01."),
    "mi21": ("The Refugees", ["hale", "crane", "ilse"], {"watch": {"min": 12}}, ["refugees_admitted", "refugees_turned"], "Ethics; Town; serious tone."),
    "mi22": ("The Wager", ["vane", "crane", "quenn"], {"flags_all": ["met_crane", "met_vane"]}, ["wager_on", "clue_crane_counts"], "Comic; clue 9."),
    "mi23": ("The Missing Windlass", ["dace", "mirren", "bram", "ilse", "wren"], {"flags_all": ["met_mirren", "met_bram"]}, ["windlass_missing", "windlass_blamed_hullfolk"], "Town vs Hullfolk."),
    "mi24": ("The Night Boat", ["solas", "crane"], {"flags_all": ["met_solas"]}, ["night_passages", "reeds_cargo"], "MA07 lead-in."),
    "mi25": ("Quenn's Budget", ["quenn", "pell", "tamm"], {"flags_all": ["met_quenn"]}, ["budget_repairs", "gates_leaking", "gates_repaired", "counter repairs_deferred"], "Coffers; feeds MA01 and water drift."),
    "mi26": ("Petronel's Fiddle", ["petronel", "wren", "vosk", "bram"], {"flags_all": ["met_wren"]}, ["fiddle_impounded", "fiddle_returned", "met_petronel"], "Song lead-in; feeds MA06."),
    "mi27": ("The Surveyor", ["vosk", "quenn"], {"watch": {"min": 18}}, ["surveyor_present", "surveyor_expelled", "clue_sluice_guard"], "Suspicion; feeds MA03."),
    "mi28": ("The Keeper's Chair", ["mirren", "tobin"], {"watch": {"min": 5}}, ["found_ledger"], "Living in Dray's house; feeds MA02."),
    "mi29": ("Hesse's Exposure", ["hesse", "fennick", "pell", "ilse"], {"flags_all": ["pressed_by_hesse"]}, ["hesse_hostile", "skimming_rumor"], "Press; Company."),
    "mi30": ("The Boundary Stone", ["ilse", "dace"], {"resources": {"town": {"max": 35}}}, ["boundary_rehearsed", "moot_called"], "Town warning; feeds MA10 and end_res_town_min."),
}

ENDINGS = [
    ("end_res_water_min", "The Dry Summit", "resource_death"), ("end_res_water_max", "The Breach", "resource_death"),
    ("end_res_traffic_min", "The Jam", "resource_death"), ("end_res_traffic_max", "The Pile-Up", "resource_death"),
    ("end_res_coffers_min", "Foreclosure", "resource_death"), ("end_res_coffers_max", "The Audit", "resource_death"),
    ("end_res_company_min", "Dismissal", "resource_death"), ("end_res_company_max", "The Promotion", "resource_death"),
    ("end_res_town_min", "Run Out", "resource_death"), ("end_res_town_max", "The Uprising", "resource_death"),
    ("end_ord_long_watch", "The Long Watch", "ordinary"), ("end_ord_transferred", "Transferred", "ordinary"),
    ("end_ord_jubilee", "The Jubilee Keeper", "ordinary"), ("end_ord_towns_keeper", "Town's Keeper", "ordinary"),
    ("end_ord_companys_keeper", "Company's Keeper", "ordinary"), ("end_ord_quiet", "A Quiet Life", "ordinary"),
    ("end_false_drought", "The Drought Report", "false"), ("end_false_killer", "Dray's Killer", "false"),
    ("end_false_purchase", "The Sorrel Purchase", "false"), ("end_false_clearance", "The Clearance", "false"),
    ("end_false_blessing", "The Dry Blessing", "false"), ("end_false_hero", "Keeper of the Courier", "false"),
    ("end_rev_sluice", "Into the Dark Water", "revelation"), ("end_rev_survey", "The Figures Do Not Close", "revelation"),
    ("end_rev_song", "The Last Verse", "revelation"), ("end_rev_letters", "What the Water Uncovered", "revelation"),
    ("end_rev_file", "Filed", "revelation"), ("end_rev_cipher", "The Gauge Speaks", "revelation"),
    ("end_rev_crane", "Duly Noted", "revelation"), ("end_rev_tobin", "Tobin's Last Story", "revelation"),
    ("end_rev_bram", "The Outfall", "revelation"), ("end_rev_vosk", "For the Record", "revelation"),
    ("end_crisis_fire", "The Boatyard Fire", "crisis"), ("end_crisis_riot", "The Riot", "crisis"),
    ("end_crisis_frost", "The Frost Closure", "crisis"), ("end_crisis_inquiry", "The Inquiry", "crisis"),
    ("end_crisis_fever", "The Fever", "crisis"),
    ("end_true_river", "The River Returned", "true"), ("end_true_ledger", "The Open Ledger", "true"),
    ("end_true_cut", "The Keeper's Cut", "true"),
]

CLUES = {
    "clue_reservoirs": "Reservoir reports never account for the level.",
    "clue_dry_aqueduct": "Aqueduct dry in summer while the pound holds.",
    "clue_iron_well": "Brewery well tastes of iron and rises with the pound.",
    "clue_song": "The Song names a river going into the hill.",
    "clue_charter": "Chapel charter thanks Marrow for the water she gave.",
    "clue_sluice_guard": "Sluice house guarded harder than a disused valve.",
    "clue_cipher": "Dray's ledger cipher keyed to the sill gauge.",
    "clue_crane_counts": "Crane's counts match Quenn's.",
    "clue_night_dredgers": "Dry Year crews came at night with no dredgers.",
    "noticed_water_fall": "The water falls every watch.",
}

TRUE_ROUTES = {
    "end_true_river": {"requires_unlocks_all": ["unlock_cut_map"], "requires_unlocks_two_of": ["unlock_quenn_survey", "unlock_lowmere_song", "unlock_marrow_letters"], "route_flag": "route_river", "allies": ["bram", "wren", "solas"], "state": {"resources": {"town": {"min": 40}}, "factions": {"hullfolk": {"min": 60}}}},
    "end_true_ledger": {"requires_unlocks_all": ["unlock_cut_map"], "requires_unlocks_two_of": ["unlock_quenn_survey", "unlock_lowmere_song", "unlock_marrow_letters"], "route_flag": "route_ledger", "allies": ["crane", "quenn", "hesse"], "state": {"resources": {"company": {"max": 60}}, "relationships": {"crane": {"min": 60}}}},
    "end_true_cut": {"requires_unlocks_all": ["unlock_cut_map"], "requires_unlocks_two_of": ["unlock_quenn_survey", "unlock_lowmere_song", "unlock_marrow_letters"], "route_flag": "route_cut", "allies": ["vosk", "hale", "tamm"], "state": {"resources": {"coffers": {"min": 60}}, "relationships": {"vosk": {"min": 60}, "hale": {"min": 50}}}},
}

UNLOCKS = {
    "unlock_drays_key": {"source_arcs": ["MA02"], "enables": ["MA11"]},
    "unlock_quenn_survey": {"source_arcs": ["MA05"], "source_endings": ["end_rev_survey"], "enables": ["end_true_ledger"]},
    "unlock_lowmere_song": {"source_arcs": ["MA06"], "source_endings": ["end_rev_song"], "enables": ["end_true_river"]},
    "unlock_marrow_letters": {"source_arcs": ["MA08"], "source_endings": ["end_rev_letters"], "enables": ["end_true_cut"]},
    "unlock_cut_map": {"source_arcs": ["MA11"], "source_endings": ["end_rev_cipher", "end_rev_bram"], "enables": ["MA12"]},
    "unlock_vosk_file": {"source_arcs": ["MA09"], "source_endings": ["end_rev_file", "end_rev_vosk"], "enables": ["end_res_company_max variant", "end_true_ledger support"]},
    "unlock_dray_fate": {"source_arcs": ["MA11"], "source_endings": ["end_rev_sluice"], "enables": ["Mirren resolution cards"]},
    "unlock_quenn_courage": {"source_arcs": ["MA05"], "enables": ["meta_quenn_braver"]},
}


def main() -> None:
    graph = {"version": 1, "major_arcs": {}, "minor_arcs": {}, "endings": [], "true_routes": TRUE_ROUTES,
             "unlocks": UNLOCKS, "clues": CLUES}
    for aid, d in MAJOR.items():
        cards = cards_by_arc[aid]
        assert len(cards) == 15, aid
        graph["major_arcs"][aid] = {
            "title": d["title"], "premise": d["premise"], "characters": d["characters"],
            "entry": d["entry"], "entry_alt": d.get("entry_alt"),
            "stages": [{"stage": i + 1, "name": s, "cards": cards[i * 3:(i + 1) * 3]} for i, s in enumerate(d["stages"])],
            "branch_points": d["branches"], "state_changes": d["state"], "success": d["success"], "failure": d["failure"],
            "delayed_consequences": d["delayed"], "cross_run_consequences": d["cross_run"], "cards": cards,
            "exit": d["exit"], "interactions": d["interactions"],
        }
    for aid, (title, chars, entry, state, note) in MINOR.items():
        cards = cards_by_arc[aid]
        assert len(cards) == 6, aid
        graph["minor_arcs"][aid] = {"title": title, "characters": chars, "entry": entry, "state_changes": state,
                                    "cards": cards, "notes": note,
                                    "stages": [{"stage": i + 1, "cards": [c]} for i, c in enumerate(cards)]}
    for eid, title, kind in ENDINGS:
        graph["endings"].append({"id": eid, "title": title, "kind": kind, "card": eid})
    OUT.write_text(json.dumps(graph, indent=1, ensure_ascii=False) + "\n")
    print(f"story graph: {len(graph['major_arcs'])} major, {len(graph['minor_arcs'])} minor, {len(graph['endings'])} endings")


if __name__ == "__main__":
    main()
