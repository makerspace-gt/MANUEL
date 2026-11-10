#!/bin/bash

set -ouex pipefail

# Copy the contents of system_files/ of the git repo to /
cp -avf "/ctx/system_files"/. /

### Install packages

# Packages can be installed from any enabled yum repo on the image.
# RPMfusion repos are available by default in ublue main images
# List of rpmfusion packages can be found here:
# https://mirrors.rpmfusion.org/mirrorlist?path=free/fedora/updates/43/x86_64/repoview/index.html&protocol=https&redirect=1

# this installs a package from fedora repos
dnf5 install -y tmux

# Use a COPR Example:
#
# dnf5 -y copr enable ublue-os/staging
# dnf5 -y install package
# Disable COPRs so they don't end up enabled on the final image:
# dnf5 -y copr disable ublue-os/staging

#### Example for enabling a System Unit File

systemctl enable podman.socket

# Tailscale is part of uCore. It connects the mini PC until NetBird runs, see docs/adr/0042-tailscale-als-uebergang-bis-netbird-nutzen.adoc
systemctl enable tailscaled.service

# Containers with a restart policy come back after a reboot
systemctl enable podman-restart.service

# Logs load, memory, GPU, temperatures and power once a minute to /var/log/manuel
systemctl enable manuel-metrics.timer

### Trust our own signing key for updates of this image
# The key is copied to /etc/pki/containers/makerspace-gt.pub by the Containerfile
jq '.transports.docker["ghcr.io/makerspace-gt/manuel"] = [{
      "type": "sigstoreSigned",
      "keyPath": "/etc/pki/containers/makerspace-gt.pub",
      "signedIdentity": {"type": "matchRepository"}
    }]' /etc/containers/policy.json > /tmp/policy.json
install -Dpm 0644 /tmp/policy.json /etc/containers/policy.json

### SSH keys of the admins, fetched from GitHub at build time
# The list of users is in build_files/github-users
# sshd reads this file via /etc/ssh/sshd_config.d/10-manuel-authorized-keys.conf
keys=/usr/share/manuel/authorized_keys/core
install -d -m 0755 "$(dirname "$keys")"
: > "$keys"
while read -r user _; do
    [[ -z "$user" || "$user" == \#* ]] && continue
    curl -fsSL --retry 3 "https://github.com/${user}.keys" | sed "s|\$| ${user}@github|" >> "$keys"
done < /ctx/github-users
chmod 0644 "$keys"
# Refuse to build an image nobody can log into
test -s "$keys"
