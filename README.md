# MANUEL
MANUEL (Minimale AI für Nutzer-Unterstützung auf Einstiegs-Level) ist ein lokales Sprachmodell für das Repair Café des Makerspace Gütersloh. Es kategorisiert Anfragen in Zammad, stellt Erstdiagnosen und schlägt Lösungen vor. Dokumentation und Einrichtung zur Nachnutzung durch andere Reparaturinitiativen.

## Betriebssystem-Image

MANUEL läuft auf einem eigenen Image auf Basis von [uCore Minimal](https://github.com/ublue-os/ucore). Es wird mit GitHub Actions täglich neu gebaut und als `ghcr.io/makerspace-gt/manuel` veröffentlicht. Ein bestehendes uCore- oder Fedora-CoreOS-System wechselt so auf das Image.

```
sudo bootc switch ghcr.io/makerspace-gt/manuel:latest
```

Die Anpassungen am Image stehen in `Containerfile`, `build_files/build.sh` und `system_files/`. Die Vorgehensweise stammt aus dem [image-template](https://github.com/ublue-os/image-template) von Universal Blue.

## Einrichtung des Images

So haben wir das Image eingerichtet. Wer MANUEL nachbauen will, geht in derselben Reihenfolge vor.

### 1 Vorlage übernehmen

1. Die Dateien aus dem [image-template](https://github.com/ublue-os/image-template) ins Repo übernehmen.
2. Im `Containerfile` das Basis-Image auf `ghcr.io/ublue-os/ucore-minimal:stable` setzen.
3. In `image-template.env` den Namen des Images und die Organisation eintragen.

### 2 Signaturschlüssel anlegen

Die Images werden mit cosign signiert. Ohne den Schlüssel schlägt der Build in GitHub Actions fehl. cosign ist im Devcontainer enthalten.

1. Ein Schlüsselpaar ohne Passwort im Wurzelverzeichnis des Repos erzeugen, weil GitHub Actions keinen passwortgeschützten Schlüssel nutzen kann.

```bash
COSIGN_PASSWORD="" cosign generate-key-pair
```

2. Den privaten Schlüssel als Secret `SIGNING_SECRET` im Repo hinterlegen, entweder in den Repo-Einstellungen unter Secrets and variables und Actions oder mit der GitHub CLI.

```bash
gh secret set SIGNING_SECRET < cosign.key
```

3. Den privaten Schlüssel zusätzlich in Vaultwarden ablegen und `cosign.key` danach lokal löschen. Aus dem GitHub-Secret lässt er sich nicht mehr auslesen. `cosign.key` steht in der `.gitignore` und darf nie committet werden.
4. Den öffentlichen Schlüssel `cosign.pub` committen und pushen.
5. Im Reiter Actions prüfen, dass der Build durchläuft.

### 3 Paket veröffentlichen

1. In den Einstellungen der Organisation unter Packages bei Package creation die Option Public erlauben. Das kann nur ein Owner der Organisation.
2. In den Einstellungen des Pakets unter Danger Zone mit Change visibility auf Public stellen.

### 4 Signaturprüfung im Image

uCore vertraut nur den Schlüsseln von Universal Blue. Damit das System auch unsere Updates prüfen kann, bringt das Image mit:

- unseren öffentlichen Schlüssel unter `/etc/pki/containers/makerspace-gt.pub`, kopiert im `Containerfile`
- eine Registry-Konfiguration unter `system_files/etc/containers/registries.d/`
- einen Eintrag in `/etc/containers/policy.json`, gesetzt in `build_files/build.sh`

### 5 SSH-Schlüssel der Admins

Die Admins stehen mit ihrem GitHub-Benutzernamen in `build_files/github-users`. Beim Build holt `build_files/build.sh` ihre öffentlichen SSH-Schlüssel von GitHub und legt sie im Image ab. Eine Konfiguration unter `system_files/etc/ssh/sshd_config.d/` sorgt dafür, dass sshd sie für den Benutzer `core` nutzt.

Neue oder entfernte Schlüssel wirken erst mit dem nächsten Build und Update. Alle Admins sollten auf GitHub die Zwei-Faktor-Authentifizierung aktiviert haben.

### 6 Butane-Datei

Die Datei [butane/manuel.bu](butane/manuel.bu) beschreibt die Installation mit Fedora CoreOS. Sie setzt Hostname und Zeitzone und wechselt beim ersten Start automatisch auf unser Image. Die Anleitung dazu steht in [butane/README.md](butane/README.md).

## Lizenz

Die Inhalte dieses Repositorys stehen unter [CC0 1.0](LICENSE). Ausgenommen sind die Dateien aus dem image-template von Universal Blue. Sie stehen unter der [Apache License 2.0](LICENSES/Apache-2.0.txt). Das sind `Containerfile`, `Justfile`, `image-template.env`, `artifacthub-repo.yml`, `build_files/`, `disk_config/` und `.github/`. Logos und Inhalte Dritter fallen ebenfalls nicht unter CC0.
