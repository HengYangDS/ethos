#!/usr/bin/env bash
# Install Node.js from an official prebuilt tarball for the hosted npm jobs.
#
# The `node:24` Docker image is only reachable through registry-1.docker.io,
# which this runner's egress blocks: every pull times out at 15s and even a
# retried job never succeeds (unlike python:3.12, which the runner keeps
# layer-cached). Rather than depend on that registry, the npm jobs run on the
# always-cached python:3.12 image and install Node from nodejs.org — the same
# egress that already serves install-lychee.sh / install-taplo.sh reliably.
# Kept outside .gitlab-ci.yml so CI stays a projection over reusable setup logic.
set -euo pipefail

version="${NODE_VERSION:-24.18.0}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../../.." && pwd)"
policy_path="${repo_root}/.config/checks/node/runtime.toml"

if command -v node >/dev/null 2>&1; then
  installed="$(node --version)"
  if [ "${installed}" = "v${version}" ]; then
    node --version
    exit 0
  fi
fi

if ! command -v curl >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends curl ca-certificates xz-utils coreutils
elif ! command -v xz >/dev/null 2>&1 || ! command -v sha256sum >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends xz-utils coreutils
fi

case "$(uname -m)" in
  x86_64|amd64) arch="x64" ;;
  aarch64|arm64) arch="arm64" ;;
  *) echo "Unsupported node architecture: $(uname -m)" >&2; exit 1 ;;
esac

if command -v python3 >/dev/null 2>&1; then
  python_command="python3"
elif command -v python >/dev/null 2>&1; then
  python_command="python"
else
  echo "Python 3 is required to read ${policy_path}" >&2
  exit 1
fi

archive_sha256="$(
  "${script_dir}/with-python-runtime.sh" -- \
    "${python_command}" - "${policy_path}" "${version}" "linux_${arch}" <<'PY_POLICY'
import re
import sys
import tomllib
from pathlib import Path

policy = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
version = sys.argv[2]
platform = sys.argv[3]
checksums = policy.get("archive_sha256", {})
digest = checksums.get(version, {}).get(platform, "")
if re.fullmatch(r"[a-f0-9]{64}", digest) is None:
    raise SystemExit(f"Node archive SHA-256 missing for {version} {platform}")
print(digest)
PY_POLICY
)"

archive="node-v${version}-linux-${arch}.tar.xz"
url="https://nodejs.org/dist/v${version}/${archive}"

cache_root="${ETHOS_CI_TOOL_CACHE_DIR:-${CI_PROJECT_DIR:-$(pwd)}/build/runtime/tool-cache/ci-tools}"
cache_dir="${cache_root}/node/${version}"
archive_path="${cache_dir}/${archive}"
persistent_cache_root="${ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR:-}"
if [ -n "${persistent_cache_root}" ]; then
  persistent_cache_dir="${persistent_cache_root}/node/${version}/linux-${arch}"
  persistent_archive_path="${persistent_cache_dir}/${archive}"
else
  persistent_cache_dir=""
  persistent_archive_path=""
fi
tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

mkdir -p "${cache_dir}"

verify_archive_checksum() {
  printf '%s  %s\n' "${archive_sha256}" "$1" | sha256sum -c -
}

if [ -n "${persistent_archive_path}" ] \
  && [ -s "${persistent_archive_path}" ] \
  && tar tJf "${persistent_archive_path}" >/dev/null 2>&1 \
  && verify_archive_checksum "${persistent_archive_path}" >/dev/null 2>&1; then
  cp "${persistent_archive_path}" "${archive_path}"
fi

if [ ! -s "${archive_path}" ] \
  || ! tar tJf "${archive_path}" >/dev/null 2>&1 \
  || ! verify_archive_checksum "${archive_path}" >/dev/null 2>&1; then
  rm -f "${archive_path}"
  echo "Installing node v${version} for linux-${arch} from ${url}"
  "${script_dir}/download-file.sh" "${url}" "${archive_path}"
fi

if ! verify_archive_checksum "${archive_path}"; then
  rm -f "${archive_path}"
  echo "Node archive checksum mismatch: ${archive}" >&2
  exit 1
fi

if [ -n "${persistent_archive_path}" ]; then
  mkdir -p "${persistent_cache_dir}"
  cp "${archive_path}" "${persistent_archive_path}.tmp"
  mv "${persistent_archive_path}.tmp" "${persistent_archive_path}"
fi

tar xJf "${archive_path}" -C "${tmpdir}"
node_dir="${tmpdir}/node-v${version}-linux-${arch}"
if [ ! -x "${node_dir}/bin/node" ]; then
  echo "node binary not found in ${archive_path}" >&2
  tar tJf "${archive_path}" >&2
  exit 1
fi
# Install into a writable prefix on PATH; the tarball bundles node, npm, and npx.
install_prefix="${ETHOS_CI_NODE_INSTALL_PREFIX:-/usr/local}"
install_bin_dir="${install_prefix}/bin"
install_lib_dir="${install_prefix}/lib"
mkdir -p "${install_bin_dir}" "${install_lib_dir}"
install -m 0755 "${node_dir}/bin/node" "${install_bin_dir}/node"
rm -rf "${install_lib_dir}/node_modules"
cp -a "${node_dir}/lib/node_modules" "${install_lib_dir}/node_modules"
ln -sf "${install_lib_dir}/node_modules/npm/bin/npm-cli.js" "${install_bin_dir}/npm"
ln -sf "${install_lib_dir}/node_modules/npm/bin/npx-cli.js" "${install_bin_dir}/npx"
export PATH="${install_bin_dir}:${PATH}"
node --version
npm --version
