# Installation

MANUEL wird als Fedora CoreOS installiert und wechselt beim ersten Start selbstständig auf unser Image `ghcr.io/makerspace-gt/manuel`. Grundlage ist die Datei [manuel.bu](manuel.bu).

## Vorbereitung

1. Prüfen, dass alle Admins in `build_files/github-users` stehen und auf GitHub einen öffentlichen SSH-Schlüssel hinterlegt haben. Die Schlüssel kommen beim Build ins Image.
2. Aus der Butane-Datei die Ignition-Datei erzeugen.

```bash
podman run --rm -i quay.io/coreos/butane:release --pretty --strict < butane/manuel.bu > manuel.ign
```

Die Datei `manuel.ign` wird nicht committet.

3. Das aktuelle Live-ISO von Fedora CoreOS herunterladen.

```bash
podman run --rm -v .:/data -w /data quay.io/coreos/coreos-installer:release download -f iso
```

4. Das ISO und `manuel.ign` auf den Ventoy-Stick kopieren.

## Installation auf dem Mini-PC

1. Den Mini-PC vom Ventoy-Stick starten und das Fedora-CoreOS-ISO auswählen.
2. Im Live-System die Ventoy-Partition einbinden, Fedora CoreOS mit der Ignition-Datei auf die interne SSD installieren und neu starten.

```bash
sudo mount -o ro /dev/disk/by-label/Ventoy /mnt
sudo coreos-installer install /dev/nvme0n1 -i /mnt/manuel.ign
sudo systemctl reboot
```

Den Namen der SSD vorher mit `lsblk` prüfen. Lässt sich die Ventoy-Partition nicht einbinden, weil Ventoy sie für das gebootete ISO belegt, liegt `manuel.ign` stattdessen auf einem zweiten USB-Stick.

## Was beim ersten Start passiert

1. Fedora CoreOS richtet Benutzer, Hostname und Zeitzone ein.
2. Das System wechselt unsigniert auf unser Image und startet neu. Unsigniert ist nötig, weil Fedora CoreOS unseren Schlüssel noch nicht kennt.
3. Unser Image bringt den Schlüssel mit. Das System wechselt deshalb auf das signierte Image und startet erneut.

Danach ist der Stand mit diesem Befehl prüfbar.

```bash
rpm-ostree status
```

Die Zeile mit dem gebooteten Image muss mit `ostree-image-signed:docker://ghcr.io/makerspace-gt/manuel:latest` beginnen.
