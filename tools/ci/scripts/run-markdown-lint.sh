#!/usr/bin/env bash
# Run the Markdown lint gate. Policy lives in
# .config/checks/markdown/.markdownlint-cli2.yaml. Lint-only: markdownlint-cli2
# never rewrites files, so the gate is safe over the sha256-content-pinned
# governance documents (evidence/ is excluded by the config regardless).
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --all-packages --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

# markdownlint-cli2 is a Node CLI; ensure a Node toolchain is present (the CI
# image installs it via install-node.sh, local developers via their own Node).
if ! command -v npx >/dev/null 2>&1; then
  "${script_dir}/install-node.sh"
fi

version="${MARKDOWNLINT_CLI2_VERSION:-0.18.1}"

npx --yes "markdownlint-cli2@${version}" \
  --config .config/checks/markdown/.markdownlint-cli2.yaml
