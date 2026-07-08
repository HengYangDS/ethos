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

if ! command -v npx >/dev/null 2>&1; then
  "tools/ci/scripts/install-node.sh"
fi

# Keep actionlint optional-by-install but real when this gate is invoked. The npm
# package bundles the Go binary for common CI platforms.
npx --yes "actionlint@${version}" "${workflow}"
