#!/usr/bin/env python3
"""Decides whether MANUEL enters a classification or asks back.

Besides the threshold there are two rules from evaluating the confident errors, see docs/einordnung.md,
step 16. R1 asks back for collective terms whose type the team wants to distinguish. R2 asks back
if the choice is a component or the subject names a service, because then the device is
usually only in the message. If the message names exactly one type for a collective term, the
follow-up question is dropped, see from_message.
"""

import re

THRESHOLD = 0.7

# R1, entries and names for which the team wants to ask back, see gleichwertig.tsv
COLLECTIVE_ENTRIES = {
    "Kaffeemaschine", "Mixer", "Ladegerät", "Lautsprecher(boxen)", "Fotoapparat", "Projektor",
    "Grill", "Heizung", "Kopfhörer", "Funkkopfhörer", "Headset",
}
COLLECTIVE_NAMES = {"Kopfhörer", "Kamera", "Lautsprecher", "Mixer", "Kaffeemaschine", "Ladegerät", "Projektor", "Grill", "Heizung"}

# R2, components instead of devices and services in the subject
COMPONENTS = {
    "Software", "Display", "USB-Stick", "Gehäuse", "Festplatte", "Akku", "Kabel", "Netzteil", "Stecker", "Adapter",
}
SERVICE = re.compile(r"install|linux|dualboot|3d[- ]?druck(?!er)", re.IGNORECASE)


# Terms in the message that resolve a collective term. If exactly one more specific entry matches,
# the follow-up question is dropped. If several or none match, it stays.
RESOLUTION = {
    "Kaffeemaschine": {
        "Pad-/Kapsel-Kaffeemaschine": r"nespresso|kapsel|senseo|dolce ?gusto|tassimo|cafissimo|\bpads?\b",
        "Kaffeevollautomat": r"vollautomat|mahlwerk|bohnen|brüheinheit|brühgruppe|\bjura\b|saeco|caffeo|magnifica",
        "Kaffeemaschine": r"filter(kaffee|maschine|automat|tüte)|glaskanne|thermoskanne",
    },
    "Mixer": {
        "Standmixer": r"standmixer|smoothie|mixbecher|mixkrug",
        "Stabmixer / Pürierstab": r"stabmixer|pürierstab|zauberstab",
        "Handmixer": r"handmixer|handrührgerät|rührbesen|knethaken",
    },
    "Kopfhörer": {
        "Kopfhörer, In-Ear": r"in[- ]?ear|earbuds|airpods|ohrhörer|ohrstöpsel",
        "Kopfhörer, On-/Over-Ear": r"over[- ]?ear|on[- ]?ear|bügel|ohrpolster",
    },
    "Funkkopfhörer": None,
    "Headset": None,
    "Lautsprecher(boxen)": {
        "Bluetooth Musikbox": r"bluetooth|\bjbl\b|musikbox|soundlink|\bue boom",
        "Soundbar": r"soundbar",
        "Aktivlautsprecher": r"aktivlautsprecher|aktive box|pc-lautsprecher|pc-boxen",
    },
    "Ladegerät": {
        "Akku Ladegerät": r"akkuladegerät|akku-ladegerät|mignon|\baaa?\b",
        "Ladegerät E-Bike": r"e-?bike|pedelec",
        "USB-Ladegerät": r"\busb\b",
        "Autobatterie-Ladegerät": r"autobatterie|kfz-batterie",
    },
    "Grill": {
        "Kontaktgrill": r"kontaktgrill|sandwich|panini|optigrill",
        "Gasgrill": r"gasgrill|gaskartusche|piezo",
        "Elektrogrill": r"elektrogrill|e-grill|tischgrill",
        "Grillofen": r"grillofen",
    },
    "Heizung": {
        "Heizlüfter": r"heizlüfter|gebläse|lüfter",
        "Elektroheizung": r"radiator|ölradiator|infrarot|konvektor|heizstrahler",
    },
    "Projektor": {
        "Diaprojektor": r"\bdias?\b|diaprojektor|kleinbild",
        "Filmprojektor": r"super ?8|schmalfilm|filmprojektor|\b8 ?mm\b|16 ?mm",
        "Beamer": r"beamer|hdmi|präsentation",
        "Space-Projektor": r"sternenhimmel|sternenprojektor|galaxy",
    },
    "Fotoapparat": {
        "Digitalkamera": r"digital|digicam|speicherkarte|sd-karte",
        "Kamera, analog": r"analog|kleinbildfilm|\bfilm\b|spiegelreflex mit film",
    },
}


RESOLUTION["Funkkopfhörer"] = RESOLUTION["Headset"] = RESOLUTION["Kopfhörer"]
RESOLUTION["Lautsprecher"] = RESOLUTION["Lautsprecher(boxen)"]
RESOLUTION["Kamera"] = RESOLUTION["Fotoapparat"]


def from_message(entry, name, text):
    """Returns the more specific entry if the message names exactly one, otherwise None.

    entry is the chosen entry, name the chosen name without the top category.
    """
    rules = RESOLUTION.get(entry) or RESOLUTION.get(name)
    if not rules or not text:
        return None
    hits = [specific for specific, pattern in rules.items() if re.search(pattern, text, re.IGNORECASE)]
    return hits[0] if len(hits) == 1 else None


def reason(entry, name, subject, confidence, threshold=THRESHOLD):
    """Returns the reason for a follow-up question or None if MANUEL enters the classification.

    entry is the merged entry, name the chosen name without the top category.
    """
    if confidence < threshold:
        return "unsicher"
    if entry in COLLECTIVE_ENTRIES or name in COLLECTIVE_NAMES:
        return "Sammelbegriff"
    if entry in COMPONENTS:
        return "Bauteil"
    if SERVICE.search(subject or ""):
        return "Dienstleistung"
    return None


def main():
    """Resolves collective terms in a result of real_representatives.py via the messages.

    Usage:
        python3 follow_up.py <result.jsonl> <nachrichten.json> <output.jsonl>
    """
    import json
    import sys

    result, messages_file, output = sys.argv[1:4]
    messages = json.load(open(messages_file, encoding="utf-8"))
    with open(result, encoding="utf-8") as rows, open(output, "w", encoding="utf-8") as out:
        for line in rows:
            row = json.loads(line)
            if row.get("rueckfrage") == "Sammelbegriff":
                text = row["titel"] + "\n" + (messages.get(row["id"], {}).get("text") or "")
                target = from_message(row["kategorie"], row["name"].split(" / ", 1)[-1], text)
                if target:
                    row["kategorie_vorher"], row["kategorie"] = row["kategorie"], target
                    row["rueckfrage"] = None
                    row["aufgeloest"] = "Nachricht"
            out.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
