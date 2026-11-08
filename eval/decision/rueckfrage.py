#!/usr/bin/env python3
"""Entscheidet, ob MANUEL eine Einordnung einträgt oder nachfragt.

Neben der Schwelle gibt es zwei Regeln aus der Auswertung der sicheren Fehler, siehe docs/einordnung.md,
Schritt 16. R1 fragt bei Sammelbegriffen nach, deren Bauart das Team unterscheiden will. R2 fragt nach,
wenn die Wahl ein Bauteil ist oder der Betreff eine Dienstleistung nennt, denn dann steht das Gerät
meist erst in der Nachricht.
"""

import re

SCHWELLE = 0.7

# R1, Einträge und Namen, bei denen das Team nachfragen will, siehe gleichwertig.tsv
SAMMEL_EINTRAEGE = {
    "Kaffeemaschine", "Mixer", "Ladegerät", "Lautsprecher(boxen)", "Fotoapparat", "Projektor",
    "Grill", "Heizung",
}
SAMMEL_NAMEN = {"Kopfhörer", "Kamera", "Lautsprecher", "Mixer", "Kaffeemaschine", "Ladegerät", "Projektor", "Grill", "Heizung"}

# R2, Bauteile statt Geräte und Dienstleistungen im Betreff
BAUTEILE = {
    "Software", "Display", "USB-Stick", "Gehäuse", "Festplatte", "Akku", "Kabel", "Netzteil", "Stecker", "Adapter",
}
DIENSTLEISTUNG = re.compile(r"install|linux|dualboot|3d[- ]?druck(?!er)", re.IGNORECASE)


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
