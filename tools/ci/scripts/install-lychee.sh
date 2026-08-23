#!/usr/bin/env bash
# Install lychee for hosted link checks. Kept outside .gitlab-ci.yml so CI stays
# a projection over reusable setup logic.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
policy_path="${repo_root}/.config/checks/lychee/supply.toml"
if command -v python3 >/dev/null 2>&1; then
  python_command="python3"
elif command -v python >/dev/null 2>&1; then
  python_command="python"
else
  echo "Python 3 is required to read ${policy_path}" >&2
  exit 1
fi

read -r version linux_x86_64_sha256 linux_aarch64_sha256 < <(
  "${python_command}" - "${policy_path}" <<'PY_POLICY'
import sys
import tomllib
from pathlib import Path

policy = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
checksums = policy["archive_sha256"]
print(policy["version"], checksums["linux_x86_64"], checksums["linux_aarch64"])
PY_POLICY
)

if command -v lychee >/dev/null 2>&1 \
  && [[ "$(lychee --version | awk '{print $2}')" = "${version}" ]]; then
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
  x86_64 | amd64)
    target="x86_64-unknown-linux-gnu"
    archive_sha256="${linux_x86_64_sha256}"
    ;;
  aarch64 | arm64)
    target="aarch64-unknown-linux-gnu"
    archive_sha256="${linux_aarch64_sha256}"
    ;;
  *)
    echo "Unsupported lychee architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

archive="lychee-${target}.tar.gz"
url="https://github.com/lycheeverse/lychee/releases/download/lychee-v${version}/${archive}"

cache_dir="${LYCHEE_CACHE_DIR:-${CI_PROJECT_DIR:-$(pwd)}/build/runtime/tool-cache/lychee}"
mkdir -p "${cache_dir}"
archive_path="${cache_dir}/${version}-${archive}"
partial_path="${archive_path}.part"
tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

download_archive() {
  if [ -s "${archive_path}" ] && tar tzf "${archive_path}" >/dev/null 2>&1; then
    echo "Using cached lychee archive ${archive_path}"
    return 0
  fi

  rm -f "${archive_path}"
  echo "Installing lychee ${version} for ${target} from ${url}"
  for attempt in 1 2 3; do
    echo "lychee download attempt ${attempt}/3"
    if curl --fail --location --show-error \
      --connect-timeout 30 --max-time 600 \
      --retry 8 --retry-delay 5 --retry-all-errors \
      --continue-at - \
      --output "${partial_path}" \
      "${url}"; then
      mv "${partial_path}" "${archive_path}"
      if tar tzf "${archive_path}" >/dev/null 2>&1; then
        return 0
      fi
      echo "Downloaded lychee archive is invalid; retrying" >&2
      rm -f "${archive_path}" "${partial_path}"
    fi
    sleep "$((attempt * 5))"
  done
  return 1
}

download_archive
actual_sha256="$(sha256sum "${archive_path}" | awk '{print $1}')"
if [[ "${actual_sha256}" != "${archive_sha256}" ]]; then
  echo "lychee archive checksum mismatch" >&2
  exit 1
fi
tar xzf "${archive_path}" -C "${tmpdir}"
lychee_bin="$(find "${tmpdir}" -type f -name lychee -perm /111 | head -n 1)"
if [ -z "${lychee_bin}" ]; then
  echo "lychee binary not found in ${archive}" >&2
  tar tzf "${archive_path}" >&2
  exit 1
fi
install -m 0755 "${lychee_bin}" /usr/local/bin/lychee
lychee --version
