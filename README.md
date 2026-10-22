# MANUEL
MANUEL (Minimale AI für Nutzer-Unterstützung auf Einstiegs-Level) ist ein lokales Sprachmodell für das Repair Café des Makerspace Gütersloh. Es kategorisiert Anfragen in Zammad, stellt Erstdiagnosen und schlägt Lösungen vor. Dokumentation und Einrichtung zur Nachnutzung durch andere Reparaturinitiativen.

## Betriebssystem-Image

MANUEL läuft auf einem eigenen Image auf Basis von [uCore Minimal](https://github.com/ublue-os/ucore). Es wird mit GitHub Actions täglich neu gebaut und als `ghcr.io/makerspace-gt/manuel` veröffentlicht. Ein bestehendes uCore- oder Fedora-CoreOS-System wechselt so auf das Image.

```
sudo bootc switch ghcr.io/makerspace-gt/manuel:latest
```

Die Anpassungen am Image stehen in `Containerfile`, `build_files/build.sh` und `system_files/`. Die Vorgehensweise stammt aus dem [image-template](https://github.com/ublue-os/image-template) von Universal Blue.

## Lizenz

Die Inhalte dieses Repositorys stehen unter [CC0 1.0](LICENSE). Ausgenommen sind die Dateien aus dem image-template von Universal Blue. Sie stehen unter der [Apache License 2.0](LICENSES/Apache-2.0.txt). Das sind `Containerfile`, `Justfile`, `image-template.env`, `artifacthub-repo.yml`, `build_files/`, `disk_config/` und `.github/`. Logos und Inhalte Dritter fallen ebenfalls nicht unter CC0.
