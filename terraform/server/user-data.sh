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
# The data volume is a separate Terraform resource attached after the instance
# is created, so it may not exist yet when this script starts. Wait for it
# instead of formatting a missing device.
# VERIFY: the device name AL2023 presents for /dev/sdf (often /dev/nvme1n1).
DATA_DEV=""
for _ in $(seq 1 60); do
  if [ -e /dev/sdf ]; then
    DATA_DEV="$(readlink -f /dev/sdf)"
    break
  fi
  if [ -b /dev/nvme1n1 ]; then
    DATA_DEV=/dev/nvme1n1
    break
  fi
  sleep 5
done
if [ -z "$DATA_DEV" ] || [ ! -b "$DATA_DEV" ]; then
  echo "data volume did not attach within 5 minutes" >&2
  exit 1
fi
if ! blkid "$DATA_DEV"; then
  mkfs -t xfs "$DATA_DEV"
fi
mkdir -p /data
# Mount by UUID: NVMe device names can change across a stop and start.
DATA_UUID="$(blkid -s UUID -o value "$DATA_DEV")"
grep -q "/data" /etc/fstab || echo "UUID=$DATA_UUID /data xfs defaults,nofail 0 2" >> /etc/fstab
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
