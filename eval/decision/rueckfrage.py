#!/usr/bin/env python3
"""Entscheidet, ob MANUEL eine Einordnung einträgt oder nachfragt.

Neben der Schwelle gibt es zwei Regeln aus der Auswertung der sicheren Fehler, siehe docs/einordnung.md,
Schritt 16. R1 fragt bei Sammelbegriffen nach, deren Bauart das Team unterscheiden will. R2 fragt nach,
wenn die Wahl ein Bauteil ist oder der Betreff eine Dienstleistung nennt, denn dann steht das Gerät
meist erst in der Nachricht. Nennt die Nachricht bei einem Sammelbegriff genau eine Bauart, entfällt die
Rückfrage, siehe aus_nachricht.
"""

import re

SCHWELLE = 0.7

# R1, Einträge und Namen, bei denen das Team nachfragen will, siehe gleichwertig.tsv
SAMMEL_EINTRAEGE = {
    "Kaffeemaschine", "Mixer", "Ladegerät", "Lautsprecher(boxen)", "Fotoapparat", "Projektor",
    "Grill", "Heizung", "Kopfhörer", "Funkkopfhörer", "Headset",
}
SAMMEL_NAMEN = {"Kopfhörer", "Kamera", "Lautsprecher", "Mixer", "Kaffeemaschine", "Ladegerät", "Projektor", "Grill", "Heizung"}

# R2, Bauteile statt Geräte und Dienstleistungen im Betreff
BAUTEILE = {
    "Software", "Display", "USB-Stick", "Gehäuse", "Festplatte", "Akku", "Kabel", "Netzteil", "Stecker", "Adapter",
}
DIENSTLEISTUNG = re.compile(r"install|linux|dualboot|3d[- ]?druck(?!er)", re.IGNORECASE)


# Begriffe in der Nachricht, die einen Sammelbegriff auflösen. Passt genau ein genauerer Eintrag,
# entfällt die Rückfrage. Passen mehrere oder keiner, bleibt sie.
AUFLOESUNG = {
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


AUFLOESUNG["Funkkopfhörer"] = AUFLOESUNG["Headset"] = AUFLOESUNG["Kopfhörer"]
AUFLOESUNG["Lautsprecher"] = AUFLOESUNG["Lautsprecher(boxen)"]
AUFLOESUNG["Kamera"] = AUFLOESUNG["Fotoapparat"]


def aus_nachricht(eintrag, name, text):
    """Liefert den genaueren Eintrag, wenn die Nachricht genau einen nennt, sonst None.

    eintrag ist der gewählte Eintrag, name der gewählte Name ohne Oberkategorie.
    """
    regeln = AUFLOESUNG.get(eintrag) or AUFLOESUNG.get(name)
    if not regeln or not text:
        return None
    treffer = [ziel for ziel, muster in regeln.items() if re.search(muster, text, re.IGNORECASE)]
    return treffer[0] if len(treffer) == 1 else None


def grund(eintrag, name, betreff, sicherheit, schwelle=SCHWELLE):
    """Liefert den Grund für eine Rückfrage oder None, wenn MANUEL die Einordnung einträgt.

    eintrag ist der zusammengefasste Eintrag, name der gewählte Name ohne Oberkategorie.
    """
    if sicherheit < schwelle:
        return "unsicher"
    if eintrag in SAMMEL_EINTRAEGE or name in SAMMEL_NAMEN:
        return "Sammelbegriff"
    if eintrag in BAUTEILE:
        return "Bauteil"
    if DIENSTLEISTUNG.search(betreff or ""):
        return "Dienstleistung"
    return None


def main():
    """Löst Sammelbegriffe in einem Ergebnis von echt_vertreter.py über die Nachrichten auf.

    Aufruf:
        python3 rueckfrage.py <Ergebnis.jsonl> <nachrichten.json> <Ausgabe.jsonl>
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
                target = aus_nachricht(row["kategorie"], row["name"].split(" / ", 1)[-1], text)
                if target:
                    row["kategorie_vorher"], row["kategorie"] = row["kategorie"], target
                    row["rueckfrage"] = None
                    row["aufgeloest"] = "Nachricht"
            out.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
