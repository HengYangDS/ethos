#!/usr/bin/env bash
# Install lychee for hosted link checks. Kept outside .gitlab-ci.yml so CI stays
# a projection over reusable setup logic.
set -euo pipefail

apt-get update
apt-get install -y curl
curl -sSL https://github.com/lycheeverse/lychee/releases/latest/download/lychee-x86_64-unknown-linux-gnu.tar.gz \
  | tar xz -C /usr/local/bin lychee
lychee --version
