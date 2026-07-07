#!/usr/bin/env bash
# Install taplo from a prebuilt release binary for hosted TOML lint/format checks.
#
# taplo is a Rust CLI. Its PyPI distribution ships no linux-aarch64 wheel, so on the
# ARM GitLab runner `uv run --no-project --with taplo` falls back to building the
# taplo sdist through maturin/cargo — a slow, non-deterministic build that fails on
# taplo's broken sdist workspace. Downloading the prebuilt release binary for the
# runner architecture avoids the Rust build entirely.
#
# Kept outside .gitlab-ci.yml so CI stays a projection over reusable setup logic
# (mirrors .config/ci/scripts/install-lychee.sh).
set -euo pipefail

if command -v taplo >/dev/null 2>&1; then
  # Local developers (e.g. `brew install taplo`) already have it; skip the download.
  taplo --version
  exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends curl ca-certificates gzip
elif ! command -v gunzip >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends gzip
fi

case "$(uname -m)" in
  x86_64|amd64) arch="x86_64" ;;
  aarch64|arm64) arch="aarch64" ;;
  *) echo "Unsupported taplo architecture: $(uname -m)" >&2; exit 1 ;;
esac

version="${TAPLO_VERSION:-0.10.0}"
archive="taplo-linux-${arch}.gz"
url="https://github.com/tamasfe/taplo/releases/download/${version}/${archive}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

echo "Installing taplo ${version} for linux-${arch} from ${url}"
curl --fail --location --show-error \
  --connect-timeout 20 --max-time 180 \
  --retry 5 --retry-delay 3 --retry-all-errors \
  --output "${tmpdir}/${archive}" \
  "${url}"
gunzip -c "${tmpdir}/${archive}" > "${tmpdir}/taplo"
install -m 0755 "${tmpdir}/taplo" /usr/local/bin/taplo
taplo --version
