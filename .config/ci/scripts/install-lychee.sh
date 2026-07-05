#!/usr/bin/env bash
# Install lychee for hosted link checks. Kept outside .gitlab-ci.yml so CI stays
# a projection over reusable setup logic.
set -euo pipefail

apt-get update
apt-get install -y curl

# The hosted runner is arm64 (aarch64); the previous script hard-coded the x86_64
# asset name, so `tar` found no `lychee` member and the gate failed on every pipeline.
# Resolve the asset by the actual machine architecture, and extract the binary
# wherever it sits in the archive (recent lychee tarballs nest it) rather than
# assuming a top-level member.
arch="$(uname -m)"
case "${arch}" in
  x86_64 | amd64) asset="lychee-x86_64-unknown-linux-gnu.tar.gz" ;;
  aarch64 | arm64) asset="lychee-aarch64-unknown-linux-gnu.tar.gz" ;;
  *)
    echo "unsupported architecture for lychee: ${arch}" >&2
    exit 1
    ;;
esac

url="https://github.com/lycheeverse/lychee/releases/latest/download/${asset}"
tmp="$(mktemp -d)"
curl -sSL "${url}" | tar xz -C "${tmp}"
# The binary may be at the archive root or one directory deep; find it either way.
binary="$(find "${tmp}" -type f -name lychee | head -n 1)"
if [ -z "${binary}" ]; then
  echo "lychee binary not found in ${asset}" >&2
  exit 1
fi
install -m 0755 "${binary}" /usr/local/bin/lychee
rm -rf "${tmp}"
lychee --version
