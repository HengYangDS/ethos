#!/usr/bin/env bash
# Install gitleaks from a prebuilt release binary for hosted secret scanning.
#
# gitleaks is a Go CLI with no PyPI distribution, so it cannot ride the uv
# toolchain the way the Python gates do. Downloading the prebuilt release binary
# for the runner architecture keeps the secrets gate deterministic and avoids a
# Go build in CI.
#
# Kept outside .gitlab-ci.yml so CI stays a projection over reusable setup logic
# (mirrors .config/ci/scripts/install-taplo.sh).
set -euo pipefail

version="${GITLEAKS_VERSION:-8.30.1}"

if command -v gitleaks >/dev/null 2>&1; then
  # Local developers (e.g. `brew install gitleaks`) already have it; skip the
  # download when the installed version already matches the pin.
  if [ "$(gitleaks version 2>/dev/null)" = "${version}" ]; then
    gitleaks version
    exit 0
  fi
fi

if ! command -v curl >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends curl ca-certificates tar
elif ! command -v tar >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends tar
fi

case "$(uname -m)" in
  x86_64|amd64) arch="x64" ;;
  aarch64|arm64) arch="arm64" ;;
  *) echo "Unsupported gitleaks architecture: $(uname -m)" >&2; exit 1 ;;
esac

archive="gitleaks_${version}_linux_${arch}.tar.gz"
url="https://github.com/gitleaks/gitleaks/releases/download/v${version}/${archive}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

echo "Installing gitleaks ${version} for linux-${arch} from ${url}"
curl --fail --location --show-error \
  --connect-timeout 20 --max-time 180 \
  --retry 5 --retry-delay 3 --retry-all-errors \
  --output "${tmpdir}/${archive}" \
  "${url}"
tar -xzf "${tmpdir}/${archive}" -C "${tmpdir}" gitleaks
install -m 0755 "${tmpdir}/gitleaks" /usr/local/bin/gitleaks
gitleaks version
