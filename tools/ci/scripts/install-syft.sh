#!/usr/bin/env bash
# Reuse Homebrew locally; install the pinned official archive in hosted Linux.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
policy_path="${repo_root}/.config/release/supply-chain.toml"
read -r version linux_amd64_sha256 linux_arm64_sha256 < <(
  python - "${policy_path}" <<'PY_POLICY'
import sys
import tomllib
from pathlib import Path

policy = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
checksums = policy["archive_sha256"]
print(policy["version"], checksums["linux_amd64"], checksums["linux_arm64"])
PY_POLICY
)
if command -v syft >/dev/null 2>&1 \
  && [[ "$(syft version -o json | python -c 'import json,sys; print(json.load(sys.stdin)["version"])')" = "${version}" ]]; then
  exit 0
fi
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "syft ${version} is required; install it through Homebrew" >&2
  exit 1
fi

case "$(uname -m)" in
  x86_64 | amd64)
    arch="amd64"
    sha256="${linux_amd64_sha256}"
    ;;
  aarch64 | arm64)
    arch="arm64"
    sha256="${linux_arm64_sha256}"
    ;;
  *)
    echo "unsupported syft architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

cache="${ETHOS_CI_TOOL_CACHE_DIR:-${CI_PROJECT_DIR:-$(pwd)}/build/runtime/tool-cache/ci-tools}/syft/${version}"
archive="${cache}/syft_${version}_linux_${arch}.tar.gz"
executable="${cache}/syft"
mkdir -p "${cache}"
if [[ ! -s "${archive}" ]]; then
  tools/ci/scripts/download-file.sh \
    "https://github.com/anchore/syft/releases/download/v${version}/syft_${version}_linux_${arch}.tar.gz" \
    "${archive}"
fi
printf '%s  %s\n' "${sha256}" "${archive}" | sha256sum -c -
temporary="$(mktemp -d)"
trap 'rm -rf "${temporary}"' EXIT
tar -xzf "${archive}" -C "${temporary}" syft
install -m 0755 "${temporary}/syft" "${executable}"
