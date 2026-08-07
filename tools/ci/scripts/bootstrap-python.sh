#!/usr/bin/env bash
# Synchronize the repository-local Python and OpenSpec runtimes from locked inputs.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"
export UV_PROJECT_ENVIRONMENT="${repo_root}/.venv"

if ! command -v git >/dev/null 2>&1 || ! ldconfig -p 2>/dev/null | grep -q 'libatomic\.so\.1'; then
  apt-get update
  apt-get install -y --no-install-recommends git libatomic1
fi

required_uv="0.12.2"
actual_uv="$(uv --version | awk '{print $2}')"
if [[ "${actual_uv}" != "${required_uv}" ]]; then
  printf 'uv version mismatch: expected %s, observed %s\n' "${required_uv}" "${actual_uv}" >&2
  exit 1
fi

# The OpenSpec shim execs npx. Hosted Python images do not supply Node, and
# this runner's Debian mirror can stall during apt installation. Reuse the
# checksum-pinned Node archive installer so every hosted job has node/npm/npx
# without a Debian package dependency.
if ! command -v npx >/dev/null 2>&1; then
  "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install-node.sh"
fi
uv --version
if [[ ! -x "${repo_root}/node_modules/.bin/openspec" ]]; then npm ci --ignore-scripts; fi
"${repo_root}/node_modules/.bin/openspec" --version
uv sync --locked --group dev
