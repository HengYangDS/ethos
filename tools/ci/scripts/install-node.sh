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

if command -v node >/dev/null 2>&1; then
  installed="$(node --version)"
  if [ "${installed}" = "v${version}" ]; then
    node --version
    exit 0
  fi
fi

if ! command -v curl >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends curl ca-certificates xz-utils
elif ! command -v xz >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends xz-utils
fi

case "$(uname -m)" in
  x86_64|amd64) arch="x64" ;;
  aarch64|arm64) arch="arm64" ;;
  *) echo "Unsupported node architecture: $(uname -m)" >&2; exit 1 ;;
esac

archive="node-v${version}-linux-${arch}.tar.xz"
url="https://nodejs.org/dist/v${version}/${archive}"

cache_root="${ETHOS_CI_TOOL_CACHE_DIR:-${CI_PROJECT_DIR:-$(pwd)}/build/cache/ci-tools}"
cache_dir="${cache_root}/node/${version}"
archive_path="${cache_dir}/${archive}"
tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "${cache_dir}"

if [ ! -s "${archive_path}" ] || ! tar tJf "${archive_path}" >/dev/null 2>&1; then
  rm -f "${archive_path}"
  echo "Installing node v${version} for linux-${arch} from ${url}"
  "${script_dir}/download-file.sh" "${url}" "${archive_path}"
fi

tar xJf "${archive_path}" -C "${tmpdir}"
node_dir="${tmpdir}/node-v${version}-linux-${arch}"
if [ ! -x "${node_dir}/bin/node" ]; then
  echo "node binary not found in ${archive_path}" >&2
  tar tJf "${archive_path}" >&2
  exit 1
fi
# Install into a prefix on PATH; the tarball bundles node, npm, and npx.
install -m 0755 "${node_dir}/bin/node" /usr/local/bin/node
cp -a "${node_dir}/lib/node_modules" /usr/local/lib/node_modules
ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
ln -sf /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
node --version
npm --version
