#!/usr/bin/env bash
# Run GitHub Actions workflow syntax validation. This is a provider syntax gate;
# it does not claim hosted GitHub runner status or repository proof.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

workflow=".github/workflows/ci.yml"
version="${ACTIONLINT_VERSION:-1.7.7}"

if [ ! -f "${workflow}" ]; then
  echo "GitHub workflow projection missing: ${workflow}" >&2
  exit 1
fi

if command -v actionlint >/dev/null 2>&1; then
  actionlint "${workflow}"
  exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends curl ca-certificates tar gzip
elif ! command -v tar >/dev/null 2>&1 || ! command -v gzip >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends tar gzip
fi

case "$(uname -s)" in
  Linux) os="linux" ;;
  Darwin) os="darwin" ;;
  *) echo "Unsupported actionlint OS: $(uname -s)" >&2; exit 1 ;;
esac

case "$(uname -m)" in
  x86_64|amd64) arch="amd64" ;;
  aarch64|arm64) arch="arm64" ;;
  *) echo "Unsupported actionlint architecture: $(uname -m)" >&2; exit 1 ;;
esac

archive="actionlint_${version}_${os}_${arch}.tar.gz"
url="https://github.com/rhysd/actionlint/releases/download/v${version}/${archive}"
cache_root="${ETHOS_CI_TOOL_CACHE_DIR:-${CI_PROJECT_DIR:-$(pwd)}/build/runtime/tool-cache/ci-tools}"
cache_dir="${cache_root}/actionlint/${version}/${os}-${arch}"
archive_path="${cache_dir}/${archive}"
bin_path="${cache_dir}/actionlint"
tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "${cache_dir}"

if [ ! -x "${bin_path}" ]; then
  if [ ! -s "${archive_path}" ] || ! tar tzf "${archive_path}" >/dev/null 2>&1; then
    rm -f "${archive_path}"
    echo "Installing actionlint ${version} for ${os}-${arch} from ${url}"
    "${script_dir}/download-file.sh" "${url}" "${archive_path}"
  fi

  if ! tar tzf "${archive_path}" | grep -qx 'actionlint'; then
    echo "actionlint binary not found in ${archive_path}" >&2
    tar tzf "${archive_path}" >&2
    exit 1
  fi
  tar -xzf "${archive_path}" -C "${tmpdir}" actionlint
  install -m 0755 "${tmpdir}/actionlint" "${bin_path}"
fi

"${bin_path}" "${workflow}"
