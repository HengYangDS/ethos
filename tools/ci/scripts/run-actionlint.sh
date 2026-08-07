#!/usr/bin/env bash
# Run GitHub Actions workflow syntax validation. This is a provider syntax gate;
# it does not claim hosted GitHub runner status or repository proof.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

workflow=".github/workflows/ci.yml"
version="${ACTIONLINT_VERSION:-1.7.7}"
# Pinned SHA-256 values for the default version. Deliberate version changes must update this pin.
ACTIONLINT_DARWIN_AMD64_SHA256="${ACTIONLINT_DARWIN_AMD64_SHA256:-28e5de5a05fc558474f638323d736d822fff183d2d492f0aecb2b73cc44584f5}"
ACTIONLINT_DARWIN_ARM64_SHA256="${ACTIONLINT_DARWIN_ARM64_SHA256:-2693315b9093aeacb4ebd91a993fea54fc215057bf0da2659056b4bc033873db}"
ACTIONLINT_LINUX_AMD64_SHA256="${ACTIONLINT_LINUX_AMD64_SHA256:-023070a287cd8cccd71515fedc843f1985bf96c436b7effaecce67290e7e0757}"
ACTIONLINT_LINUX_ARM64_SHA256="${ACTIONLINT_LINUX_ARM64_SHA256:-401942f9c24ed71e4fe71b76c7d638f66d8633575c4016efd2977ce7c28317d0}"

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
  *)
    echo "Unsupported actionlint OS: $(uname -s)" >&2
    exit 1
    ;;
esac

case "$(uname -m)" in
  x86_64 | amd64) arch="amd64" ;;
  aarch64 | arm64) arch="arm64" ;;
  *)
    echo "Unsupported actionlint architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

case "${os}-${arch}" in
  darwin-amd64) archive_sha256="${ACTIONLINT_DARWIN_AMD64_SHA256}" ;;
  darwin-arm64) archive_sha256="${ACTIONLINT_DARWIN_ARM64_SHA256}" ;;
  linux-amd64) archive_sha256="${ACTIONLINT_LINUX_AMD64_SHA256}" ;;
  linux-arm64) archive_sha256="${ACTIONLINT_LINUX_ARM64_SHA256}" ;;
  *)
    echo "Unsupported actionlint platform: ${os}-${arch}" >&2
    exit 1
    ;;
esac

archive="actionlint_${version}_${os}_${arch}.tar.gz"
url="https://github.com/rhysd/actionlint/releases/download/v${version}/${archive}"
cache_root="${ETHOS_CI_TOOL_CACHE_DIR:-${CI_PROJECT_DIR:-$(pwd)}/build/runtime/tool-cache/ci-tools}"
cache_dir="${cache_root}/actionlint/${version}/${os}-${arch}"
archive_path="${cache_dir}/${archive}"
bin_path="${cache_dir}/actionlint"
persistent_cache_root="${ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR:-}"
if [ -n "${persistent_cache_root}" ]; then
  persistent_cache_dir="${persistent_cache_root}/actionlint/${version}/${os}-${arch}"
  persistent_archive_path="${persistent_cache_dir}/${archive}"
else
  persistent_cache_dir=""
  persistent_archive_path=""
fi
tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "${cache_dir}"

verify_archive_checksum() {
  printf '%s  %s\n' "${archive_sha256}" "$1" | sha256sum -c -
}

if [ ! -x "${bin_path}" ]; then
  if [ -n "${persistent_archive_path}" ] \
    && [ -s "${persistent_archive_path}" ] \
    && tar tzf "${persistent_archive_path}" >/dev/null 2>&1 \
    && verify_archive_checksum "${persistent_archive_path}" >/dev/null 2>&1; then
    cp "${persistent_archive_path}" "${archive_path}"
  fi

  if [ ! -s "${archive_path}" ] \
    || ! tar tzf "${archive_path}" >/dev/null 2>&1 \
    || ! verify_archive_checksum "${archive_path}" >/dev/null 2>&1; then
    rm -f "${archive_path}"
    echo "Installing actionlint ${version} for ${os}-${arch} from ${url}"
    "${script_dir}/download-file.sh" "${url}" "${archive_path}"
  fi

  verify_archive_checksum "${archive_path}"
  if [ -n "${persistent_archive_path}" ]; then
    mkdir -p "${persistent_cache_dir}"
    cp "${archive_path}" "${persistent_archive_path}.tmp"
    mv "${persistent_archive_path}.tmp" "${persistent_archive_path}"
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
