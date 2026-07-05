#!/usr/bin/env bash
# Install lychee for hosted link checks. Kept outside .gitlab-ci.yml so CI stays
# a projection over reusable setup logic.
set -euo pipefail

if command -v lychee >/dev/null 2>&1; then
  lychee --version
  exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends curl ca-certificates tar
elif ! command -v tar >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends tar
fi

case "$(uname -m)" in
  x86_64|amd64) target="x86_64-unknown-linux-gnu" ;;
  aarch64|arm64) target="aarch64-unknown-linux-gnu" ;;
  *) echo "Unsupported lychee architecture: $(uname -m)" >&2; exit 1 ;;
esac

version="${LYCHEE_VERSION:-latest}"
archive="lychee-${target}.tar.gz"
if [ "${version}" = "latest" ]; then
  url="https://github.com/lycheeverse/lychee/releases/latest/download/${archive}"
else
  url="https://github.com/lycheeverse/lychee/releases/download/${version}/${archive}"
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

echo "Installing lychee ${version} for ${target} from ${url}"
curl --fail --location --show-error \
  --connect-timeout 20 --max-time 180 \
  --retry 5 --retry-delay 3 --retry-all-errors \
  --output "${tmpdir}/${archive}" \
  "${url}"
tar xzf "${tmpdir}/${archive}" -C "${tmpdir}"
lychee_bin="$(find "${tmpdir}" -type f -name lychee -perm /111 | head -n 1)"
if [ -z "${lychee_bin}" ]; then
  echo "lychee binary not found in ${archive}" >&2
  tar tzf "${tmpdir}/${archive}" >&2
  exit 1
fi
install -m 0755 "${lychee_bin}" /usr/local/bin/lychee
lychee --version
