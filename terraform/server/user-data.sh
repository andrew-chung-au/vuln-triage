#!/usr/bin/env bash
# Server bootstrap (task 17 / #141). Runs once at first boot on Amazon Linux
# 2023. Installs Docker, the Compose plugin and Caddy (the reverse proxy), and
# mounts the data volume. The actual app images are deployed later by the CI
# workflow via SSM (not here). VERIFY: package names and paths on AL2023.
set -euxo pipefail

# --- Docker + Compose plugin ------------------------------------------------
dnf -y update
dnf -y install docker
systemctl enable --now docker

# Compose v2 plugin.
mkdir -p /usr/local/lib/docker/cli-plugins
ARCH="$(uname -m)"
# VERIFY: pin the Compose plugin version at apply time.
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${ARCH}" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# --- Mount the data volume at /data ----------------------------------------
# VERIFY: the device name AL2023 presents for /dev/sdf (often /dev/nvme1n1).
DATA_DEV="$(readlink -f /dev/sdf || echo /dev/nvme1n1)"
if ! blkid "$DATA_DEV"; then
  mkfs -t xfs "$DATA_DEV"
fi
mkdir -p /data
grep -q "/data" /etc/fstab || echo "$DATA_DEV /data xfs defaults,nofail 0 2" >> /etc/fstab
mount -a

# --- Caddy (reverse proxy; automatic Let's Encrypt) -------------------------
# Run Caddy as a container so no OS package is needed. The Caddyfile is placed
# by the deploy workflow alongside the dev/prod Compose projects; this bootstrap
# only creates the directory and a docker network the projects share with Caddy.
mkdir -p /opt/vuln-triage
docker network create vt-edge || true

# The dev and prod Compose projects and the Caddyfile are delivered by the
# first deploy (CI via SSM). Caddy is started by that same deploy once the
# Caddyfile and the project services exist on the shared vt-edge network.
echo "bootstrap complete" > /opt/vuln-triage/bootstrap.done
