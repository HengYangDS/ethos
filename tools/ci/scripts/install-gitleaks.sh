#!/usr/bin/env bash
# Install gitleaks from a prebuilt release binary for hosted secret scanning.
#
# gitleaks is a Go CLI with no PyPI distribution, so it cannot ride the uv
# toolchain the way the Python gates do. Downloading the prebuilt release binary
# for the runner architecture keeps the secrets gate deterministic and avoids a
# Go build in CI.
#
# Kept outside .gitlab-ci.yml so CI stays a projection over reusable setup logic
# (mirrors tools/ci/scripts/install-taplo.sh).
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

cache_root="${ETHOS_CI_TOOL_CACHE_DIR:-${CI_PROJECT_DIR:-$(pwd)}/build/cache/ci-tools}"
cache_dir="${cache_root}/gitleaks/${version}"
archive_path="${cache_dir}/${archive}"
tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "${cache_dir}"

if [ ! -s "${archive_path}" ] || ! tar tzf "${archive_path}" >/dev/null 2>&1; then
  rm -f "${archive_path}"
  echo "Installing gitleaks ${version} for linux-${arch} from ${url}"
  "${script_dir}/download-file.sh" "${url}" "${archive_path}"
fi

if ! tar tzf "${archive_path}" | grep -qx 'gitleaks'; then
  echo "gitleaks binary not found in ${archive_path}" >&2
  tar tzf "${archive_path}" >&2
  exit 1
fi

tar -xzf "${archive_path}" -C "${tmpdir}" gitleaks
install -m 0755 "${tmpdir}/gitleaks" /usr/local/bin/gitleaks
gitleaks version
