#!/usr/bin/env bash
# Shared GitLab Python bootstrap. CI YAML is a provider projection; this script is
# the local SSOT for Python/uv/OpenSpec setup used by hosted jobs.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
# Hosted owner scripts use `uv run --no-sync` after bootstrap. Materialize the
# same checkout-bound environment first so they cannot fall back to a default
# `.venv` or ambient interpreter.
export UV_PROJECT_ENVIRONMENT="${repo_root}/build/runtime/venv"
bootstrap_venv="${repo_root}/build/runtime/tool-cache/uv-bootstrap"
bootstrap_python="${ETHOS_BOOTSTRAP_PYTHON:-python3}"
"${bootstrap_python}" -m venv "${bootstrap_venv}"
"${bootstrap_venv}/bin/pip" install --disable-pip-version-check --quiet 'uv==0.11.29'
export PATH="${bootstrap_venv}/bin:${PATH}"

# The OpenSpec shim execs npx. Hosted Python images do not supply Node, and
# this runner's Debian mirror can stall during apt installation. Reuse the
# checksum-pinned Node archive installer so every hosted job has node/npm/npx
# without a Debian package dependency.
if ! command -v npx >/dev/null 2>&1; then
  "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install-node.sh"
fi
openspec_shim="${bootstrap_venv}/bin/openspec"
printf '%s\n' '#!/usr/bin/env bash' 'exec npx --yes @fission-ai/openspec@1.6.0 "$@"' > "${openspec_shim}"
chmod +x "${openspec_shim}"
if [[ -n "${GITHUB_PATH:-}" ]]; then printf '%s\n' "${bootstrap_venv}/bin" >> "${GITHUB_PATH}"; fi
uv --version
uv sync --group dev
