#!/usr/bin/env python3
"""Build content/CARD_INVENTORY.json: exactly 1,000 reserved card IDs.

The inventory is the authoritative count. tools/validate_content.py fails if the
set of produced card IDs differs from the inventory set. Statuses are refreshed
by validate_content.py --update-inventory (planned -> written when the card exists).
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "content" / "CARD_INVENTORY.json"

MAJOR = ["vosk", "pell", "quenn", "ilse", "mirren", "bram", "wren", "crane", "vane", "solas", "hale", "fennick"]
RESOURCES = ["water", "traffic", "coffers", "company", "town"]

entries = []


def add(cid, category, speaker, purpose, resource="", arc="", prereq="none"):
    entries.append({
        "id": cid, "category": category, "speaker": speaker, "purpose": purpose,
        "resource": resource, "arc": arc, "prerequisites": prereq, "status": "planned",
    })


# 1. Onboarding (30)
ONB = [
    ("pell", "Pell welcomes the new Keeper and hands over the toll book.", "company"),
    ("src_gate", "First vessel: a grain barge; open the gate or check papers.", "traffic"),
    ("mirren", "Mirren shows the paddles; her father's oilskin.", "town"),
    ("src_weather", "The gauge shows the water a mark lower than yesterday.", "water"),
    ("ilse", "Ilse names the price of a room and a welcome.", "town"),
    ("src_telegram", "Company telegram: report traffic figures by the watch.", "company"),
    ("quenn", "Quenn asks for repair money on the first day.", "coffers"),
    ("src_gate", "A Hullfolk boat asks passage without fee.", "traffic"),
    ("vosk", "Vosk introduces herself and reads your first entries.", "company"),
    ("crane", "Crane presents the Compact and Schedule Four.", "traffic"),
    ("vane", "Vane presents a delay bill and a rate card.", "coffers"),
    ("fennick", "Fennick offers a confidence about the last Keeper.", "town"),
    ("src_gate", "A pilgrim boat asks a blessing before passage.", "water"),
    ("bram", "Bram asks whether the new Keeper is a gate or a wall.", "town"),
    ("wren", "Wren offers a small favor.", "coffers"),
    ("src_ledger", "Dray's chair; the study door is locked.", "town"),
    ("hale", "Hale blesses the gates and mentions the gift.", "water"),
    ("solas", "Solas asks how the Keeper wants convoys handled.", "traffic"),
    ("dace", "Dace lists three things wrong with the gates.", "coffers"),
    ("src_weather", "Rain; the pound rises a little; cellars complain.", "water"),
    ("pell", "Pell asks for a first throughput target.", "traffic"),
    ("src_gate", "Two boats arrive together; who goes first.", "traffic"),
    ("ilse", "The inn asks for the Keeper's custom, or the Company store's.", "town"),
    ("src_telegram", "Aldmere wire: grain must not be delayed.", "company"),
    ("mirren", "Mirren asks if the Keeper has opened the study.", "town"),
    ("stroud", "Stroud warns about fatigue and the watch bell.", "town"),
    ("vosk", "Vosk's first observation on toll irregularity.", "coffers"),
    ("src_weather", "A dry week: the aqueduct is a trickle, the pound holds (clue).", "water"),
    ("src_gate", "A late boat asks night passage.", "traffic"),
    ("src_ledger", "End of the first watches: what kind of Keeper this will be.", "company"),
]
for i, (spk, purpose, res) in enumerate(ONB, 1):
    add(f"onb_{i:02d}", "onboarding", spk, purpose, res, prereq="watch<=8")

# 2. Evergreen (220): 11 themes x 20
EVG_THEMES = [
    ("cargo", ["src_gate", "crane", "vane", "wren", "dace"], "Cargo and inspection dilemmas at the gate", "traffic"),
    ("tolls", ["src_gate", "ilse", "vane", "cole", "vosk"], "Tolls, scrip, bribes and the toll book", "coffers"),
    ("order", ["src_gate", "crane", "pell", "solas", "src_stranger"], "Order of passage, queues and precedence", "traffic"),
    ("weather", ["src_weather", "quenn", "dace", "tamm", "hale"], "Weather, seasons and water management", "water"),
    ("town_life", ["ilse", "cole", "stroud", "src_stranger", "dace"], "Town life, rents, work, festivals", "town"),
    ("company_orders", ["src_telegram", "pell", "vosk", "kell", "fennick"], "Company directives and reports", "company"),
    ("hullfolk", ["bram", "wren", "petronel", "src_gate", "ilse"], "Hullfolk moorings, customs, friction", "town"),
    ("shores", ["crane", "vane", "solas", "src_telegram", "hesse"], "Aldmere-Sorrel rivalry at the summit", "traffic"),
    ("chapel", ["hale", "src_stranger", "cole", "bram", "ilse"], "The Concordance, rites, mercy at the gate", "water"),
    ("maintenance", ["quenn", "tamm", "dace", "mirren", "src_weather"], "Gates, paddles, repairs and deferrals", "coffers"),
    ("strangers", ["src_stranger", "src_gate", "hesse", "tobin", "stroud"], "Petitioners, travellers, oddities", "town"),
]
for theme, speakers, desc, res in EVG_THEMES:
    for n in range(1, 21):
        spk = speakers[(n - 1) % len(speakers)]
        add(f"evg_{theme}_{n:02d}", "evergreen", spk, f"{desc} ({n}).", res)

# 3. Resource-reactive (150): 30 per resource, 15 low-band, 15 high-band
RES_SPEAKERS = {
    "water": ["src_weather", "quenn", "bram", "ilse", "hale", "dace", "tamm", "mirren"],
    "traffic": ["src_gate", "vane", "crane", "pell", "solas", "dace", "wren", "hesse"],
    "coffers": ["cole", "vosk", "ilse", "quenn", "dace", "vane", "pell", "src_ledger"],
    "company": ["pell", "vosk", "kell", "src_telegram", "fennick", "hesse", "crane", "quenn"],
    "town": ["ilse", "dace", "cole", "stroud", "src_stranger", "hesse", "tobin", "mirren"],
}
for res in RESOURCES:
    for n in range(1, 31):
        band = "low" if n <= 15 else "high"
        spk = RES_SPEAKERS[res][(n - 1) % 8]
        add(f"res_{res}_{n:02d}", "resources", spk,
            f"Reacts to {band} {res}: {'danger and recovery' if band == 'low' else 'excess and its costs'} ({n}).",
            res, prereq=f"{res} {'<=35' if band == 'low' else '>=65'}")

# 4. Relationships (120): 10 per major
REL_RES = {"vosk": "company", "pell": "company", "quenn": "coffers", "ilse": "town", "mirren": "town", "bram": "town",
           "wren": "coffers", "crane": "traffic", "vane": "traffic", "solas": "traffic", "hale": "water", "fennick": "company"}
for ch in MAJOR:
    for n in range(1, 11):
        stage = "introduction" if n <= 2 else "trust or friction" if n <= 6 else "high-trust or estranged"
        add(f"rel_{ch}_{n:02d}", "relationships", ch, f"Relationship card for {ch}: {stage} ({n}).", REL_RES[ch],
            prereq="met flag; relationship band")

# 5. Minor arcs (30 x 6 = 180)
MINOR = [
    ("mi01", "The Geese", ["src_gate", "ilse", "dace", "src_stranger", "ilse", "src_ledger"], "town"),
    ("mi02", "The Duel of Precedence", ["crane", "vane", "crane", "solas", "vane", "crane"], "traffic"),
    ("mi03", "Iron Spring", ["stroud", "ilse", "stroud", "ilse", "quenn", "ilse"], "water"),
    ("mi04", "The Blessing of Coal", ["vane", "hale", "vane", "hale", "src_gate", "hale"], "traffic"),
    ("mi05", "Dace's Three Things", ["dace", "dace", "pell", "dace", "ilse", "dace"], "town"),
    ("mi06", "The Loan", ["cole", "cole", "src_ledger", "cole", "ilse", "cole"], "coffers"),
    ("mi07", "The Courier's Headline", ["hesse", "fennick", "hesse", "pell", "hesse", "src_telegram"], "company"),
    ("mi08", "Tobin's Dry Year", ["tobin", "tobin", "mirren", "tobin", "vosk", "tobin"], "water"),
    ("mi09", "The Pilgrims", ["hale", "src_stranger", "crane", "hale", "src_gate", "hale"], "water"),
    ("mi10", "The Drover", ["src_stranger", "crane", "src_stranger", "dace", "src_stranger", "ilse"], "water"),
    ("mi11", "The Runaway", ["mirren", "src_stranger", "solas", "mirren", "solas", "src_ledger"], "town"),
    ("mi12", "Fever Boat", ["src_gate", "stroud", "vosk", "stroud", "ilse", "stroud"], "traffic"),
    ("mi13", "The Telegram Habit", ["fennick", "src_telegram", "fennick", "vosk", "fennick", "src_ledger"], "company"),
    ("mi14", "The Scrip Riot", ["ilse", "pell", "cole", "ilse", "dace", "pell"], "coffers"),
    ("mi15", "Wren's Favor", ["wren", "wren", "src_gate", "wren", "bram", "wren"], "coffers"),
    ("mi16", "The Frost", ["src_weather", "dace", "vane", "quenn", "ilse", "src_weather"], "traffic"),
    ("mi17", "The Lamp Vigil", ["hale", "bram", "hale", "petronel", "src_ledger", "hale"], "water"),
    ("mi18", "Tamm's Hull", ["tamm", "wren", "tamm", "crane", "wren", "tamm"], "traffic"),
    ("mi19", "The Rent", ["cole", "ilse", "cole", "src_stranger", "ilse", "cole"], "town"),
    ("mi20", "The Commissioner's Visit", ["src_telegram", "pell", "kell", "vosk", "kell", "pell"], "company"),
    ("mi21", "The Refugees", ["src_gate", "hale", "crane", "ilse", "src_stranger", "hale"], "town"),
    ("mi22", "The Wager", ["vane", "crane", "quenn", "vane", "crane", "src_ledger"], "water"),
    ("mi23", "The Missing Windlass", ["dace", "mirren", "bram", "ilse", "wren", "mirren"], "town"),
    ("mi24", "The Night Boat", ["src_gate", "solas", "src_gate", "crane", "solas", "src_ledger"], "traffic"),
    ("mi25", "Quenn's Budget", ["quenn", "pell", "quenn", "tamm", "pell", "quenn"], "coffers"),
    ("mi26", "Petronel's Fiddle", ["petronel", "wren", "vosk", "petronel", "bram", "petronel"], "coffers"),
    ("mi27", "The Surveyor", ["src_stranger", "vosk", "src_stranger", "quenn", "vosk", "src_ledger"], "company"),
    ("mi28", "The Keeper's Chair", ["src_ledger", "mirren", "src_ledger", "tobin", "mirren", "src_ledger"], "town"),
    ("mi29", "Hesse's Exposure", ["hesse", "fennick", "pell", "hesse", "ilse", "hesse"], "company"),
    ("mi30", "The Boundary Stone", ["ilse", "dace", "src_stranger", "ilse", "src_ledger", "ilse"], "town"),
]
assert len(MINOR) == 30
for aid, title, spks, res in MINOR:
    for s in range(1, 7):
        add(f"{aid}_{s}", "minor_arcs", spks[s - 1], f"{title}, beat {s} of 6.", res, aid,
            prereq="arc entry" if s == 1 else f"arc {aid} stage {s - 1}")

# 6. Major arcs (12 x 15 = 180): 5 stages x 3 cards
MAJOR_ARCS = [
    ("MA01", "The Jubilee", ["pell", "quenn", "kell", "pell", "ilse"], "company"),
    ("MA02", "The Study", ["mirren", "fennick", "tobin", "mirren", "src_ledger"], "town"),
    ("MA03", "The Auditor's Interest", ["vosk", "fennick", "vosk", "vosk", "vosk"], "company"),
    ("MA04", "Throughput", ["pell", "vane", "crane", "src_gate", "pell"], "traffic"),
    ("MA05", "The Reservoir Sums", ["quenn", "quenn", "crane", "vosk", "quenn"], "water"),
    ("MA06", "The Water Debt", ["bram", "petronel", "wren", "bram", "bram"], "town"),
    ("MA07", "The Rifle Road", ["wren", "solas", "crane", "vane", "solas"], "traffic"),
    ("MA08", "High Water", ["ilse", "hale", "stroud", "hale", "cole"], "water"),
    ("MA09", "The Vosk File", ["fennick", "hesse", "crane", "hesse", "vosk"], "company"),
    ("MA10", "The Clearance", ["pell", "ilse", "bram", "solas", "bram"], "town"),
    ("MA11", "Into the Cut", ["mirren", "bram", "src_ledger", "tamm", "mirren"], "water"),
    ("MA12", "Last Water", ["src_ledger", "vosk", "bram", "quenn", "hale"], "water"),
]
assert len(MAJOR_ARCS) == 12
STAGE_NAMES = {
    "MA01": ["Plan", "Budget", "Rehearsal", "Ceremony", "Aftermath"],
    "MA02": ["Locked drawer", "Cipher", "Gauge", "Wire copy", "Key"],
    "MA03": ["Inspection", "Questions", "The Sluice House", "Offer", "Verdict"],
    "MA04": ["Record", "Corners", "Inspectors", "Night passages", "Reckoning"],
    "MA05": ["Drawer", "Aqueduct walk", "Crane's figures", "Drought or Cut", "Publish or burn"],
    "MA06": ["Mooring", "The remembered", "The Song", "The outfall", "The debt named"],
    "MA07": ["Crate", "Buyer", "Compact seals", "Convoy", "Choice"],
    "MA08": ["Cellars", "Undercroft", "The well", "The letters", "The charter"],
    "MA09": ["Rumor", "The copy", "Leverage", "Press", "File"],
    "MA10": ["Draft", "Moot", "Order", "The Reach", "Aftermath"],
    "MA11": ["Door", "Descent", "What is found", "Return", "Telling Mirren"],
    "MA12": ["Allies", "Plan", "The night", "The sluice", "Dawn"],
}
for aid, title, stage_speakers, res in MAJOR_ARCS:
    n = 0
    for stage in range(1, 6):
        for beat in range(1, 4):
            n += 1
            add(f"{aid.lower()}_{n:02d}", "major_arcs", stage_speakers[stage - 1],
                f"{title}: stage {stage} '{STAGE_NAMES[aid][stage - 1]}', beat {beat}.", res, aid,
                prereq="arc entry" if n == 1 else f"arc {aid} stage {stage}")

# 7. Crises (70)
CRISES = [
    # (id_base, count, speakers, purpose, resource)
    ("cri_flood", 8, ["src_weather", "ilse", "dace", "quenn", "hale", "stroud", "src_weather", "src_ledger"],
     "Escalating high-water emergency toward the Breach", "water"),
    ("cri_dry", 8, ["src_weather", "quenn", "bram", "src_gate", "vane", "pell", "dace", "src_ledger"],
     "Escalating low-water emergency toward the Dry Summit", "water"),
    ("cri_jam", 7, ["src_gate", "vane", "crane", "dace", "pell", "solas", "src_ledger"],
     "Queue crisis toward the Jam", "traffic"),
    ("cri_pileup", 6, ["src_gate", "dace", "stroud", "vosk", "crane", "src_ledger"],
     "Chamber collision and inquiry", "traffic"),
    ("cri_money", 7, ["cole", "vosk", "dace", "ilse", "kell", "src_telegram", "src_ledger"],
     "Wages, debt, audit and foreclosure", "coffers"),
    ("cri_company", 6, ["src_telegram", "vosk", "kell", "pell", "fennick", "src_ledger"],
     "Company confidence collapse or dangerous favor", "company"),
    ("cri_town", 8, ["ilse", "dace", "src_stranger", "cole", "hesse", "solas", "ilse", "src_ledger"],
     "Town unrest toward Run Out or Uprising", "town"),
    ("cri_fire", 5, ["tamm", "dace", "stroud", "ilse", "src_ledger"], "Fire at the boatyard", "town"),
    ("cri_frost", 5, ["src_weather", "dace", "vane", "stroud", "src_ledger"], "Frost closure and shortage", "traffic"),
    ("cri_fever", 5, ["stroud", "vosk", "hale", "ilse", "src_ledger"], "Fever outbreak and quarantine", "town"),
    ("cri_recover", 5, ["src_ledger", "tobin", "hale", "ilse", "pell"], "Recovery opportunities after a crisis", "company"),
]
count = 0
for base, k, spks, purpose, res in CRISES:
    for n in range(1, k + 1):
        add(f"{base}_{n:02d}", "crises", spks[(n - 1) % len(spks)], f"{purpose} ({n} of {k}).", res,
            prereq="crisis pool trigger")
        count += 1
assert count == 70, count

# 8. Endings and metaprogression (50)
END = [
    # resource deaths (10)
    ("end_res_water_min", "src_weather", "Ending: The Dry Summit.", "water"),
    ("end_res_water_max", "src_weather", "Ending: The Breach.", "water"),
    ("end_res_traffic_min", "pell", "Ending: The Jam.", "traffic"),
    ("end_res_traffic_max", "dace", "Ending: The Pile-Up.", "traffic"),
    ("end_res_coffers_min", "kell", "Ending: Foreclosure.", "coffers"),
    ("end_res_coffers_max", "vosk", "Ending: The Audit.", "coffers"),
    ("end_res_company_min", "src_telegram", "Ending: Dismissal.", "company"),
    ("end_res_company_max", "kell", "Ending: The Promotion.", "company"),
    ("end_res_town_min", "ilse", "Ending: Run Out.", "town"),
    ("end_res_town_max", "solas", "Ending: The Uprising.", "town"),
    # ordinary successes (6)
    ("end_ord_long_watch", "src_ledger", "Ending: The Long Watch.", "company"),
    ("end_ord_transferred", "pell", "Ending: Transferred.", "company"),
    ("end_ord_jubilee", "pell", "Ending: The Jubilee Keeper.", "company"),
    ("end_ord_towns_keeper", "ilse", "Ending: Town's Keeper.", "town"),
    ("end_ord_companys_keeper", "vosk", "Ending: Company's Keeper.", "company"),
    ("end_ord_quiet", "src_ledger", "Ending: A Quiet Life.", "town"),
    # false endings (6)
    ("end_false_drought", "quenn", "False ending: The Drought Report.", "water"),
    ("end_false_killer", "vosk", "False ending: Dray's Killer.", "company"),
    ("end_false_purchase", "vane", "False ending: The Sorrel Purchase.", "traffic"),
    ("end_false_clearance", "pell", "False ending: The Clearance.", "town"),
    ("end_false_blessing", "hale", "False ending: The Dry Blessing.", "water"),
    ("end_false_hero", "hesse", "False ending: The Keeper of the Courier.", "company"),
    # revelations (10)
    ("end_rev_sluice", "src_ledger", "Revelation ending: drowned in the sluice house; Dray's fate learned.", "water"),
    ("end_rev_survey", "quenn", "Revelation ending: dismissed after the survey; survey unlocked.", "company"),
    ("end_rev_song", "petronel", "Revelation ending: run out, but the Song was learned.", "town"),
    ("end_rev_letters", "hale", "Revelation ending: the Breach reveals the undercroft letters.", "water"),
    ("end_rev_file", "fennick", "Revelation ending: audit finds the Keeper with Vosk's file.", "coffers"),
    ("end_rev_cipher", "mirren", "Revelation ending: the cipher solved on the last night.", "town"),
    ("end_rev_crane", "crane", "Revelation ending: Crane's report preserves the water counts.", "traffic"),
    ("end_rev_tobin", "tobin", "Revelation ending: Tobin's last story.", "water"),
    ("end_rev_bram", "bram", "Revelation ending: Bram names the outfall at the boundary stone.", "town"),
    ("end_rev_vosk", "vosk", "Revelation ending: Vosk's confession at dismissal.", "company"),
    # crisis endings (5)
    ("end_crisis_fire", "tamm", "Crisis ending: the boatyard fire.", "town"),
    ("end_crisis_riot", "ilse", "Crisis ending: the riot.", "town"),
    ("end_crisis_frost", "stroud", "Crisis ending: the frost closure.", "traffic"),
    ("end_crisis_inquiry", "kell", "Crisis ending: the inquiry.", "company"),
    ("end_crisis_fever", "stroud", "Crisis ending: the fever.", "town"),
    # true endings (3)
    ("end_true_river", "bram", "True ending: The River Returned.", "water"),
    ("end_true_ledger", "crane", "True ending: The Open Ledger.", "company"),
    ("end_true_cut", "vosk", "True ending: The Keeper's Cut.", "water"),
    # meta (10)
    ("meta_new_keeper_2", "src_ledger", "Run 2+ opening: the Ledger of the last Keeper.", "company"),
    ("meta_new_keeper_3", "src_ledger", "Run 3+ opening: the town remembers.", "town"),
    ("meta_town_remembers", "ilse", "Ilse recalls the previous Keeper by one act.", "town"),
    ("meta_vosk_remembers", "vosk", "Vosk: 'the last one asked that too.'", "company"),
    ("meta_hullfolk_gift", "bram", "Hullfolk gift for a chair that honored the remembered.", "town"),
    ("meta_quenn_braver", "quenn", "Quenn begins braver after a protective Keeper.", "water"),
    ("meta_ledger_cipher", "src_ledger", "Cipher progress carried in the Ledger.", "town"),
    ("meta_route_river_gate", "bram", "True-route gate: the Reed Reach asks for a promise.", "water"),
    ("meta_route_ledger_gate", "crane", "True-route gate: Crane's conditions for witness.", "company"),
    ("meta_route_cut_gate", "vosk", "True-route gate: Vosk's offer.", "water"),
]
assert len(END) == 50, len(END)
for cid, spk, purpose, res in END:
    add(cid, "endings_meta", spk, purpose, res, prereq="ending trigger or run>=2")

# Verify totals
from collections import Counter
c = Counter(e["category"] for e in entries)
expected = {"onboarding": 30, "evergreen": 220, "resources": 150, "relationships": 120,
            "minor_arcs": 180, "major_arcs": 180, "crises": 70, "endings_meta": 50}
assert dict(c) == expected, dict(c)
assert len(entries) == 1000, len(entries)
assert len({e["id"] for e in entries}) == 1000

OUT.write_text(json.dumps({"version": 1, "total": 1000, "allocation": expected, "cards": entries}, indent=1,
                          ensure_ascii=False) + "\n")
print("inventory written:", len(entries), dict(c))
