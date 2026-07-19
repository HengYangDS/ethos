#!/usr/bin/env bash
# Own staged-index secret admission only; the full tracked-tree/history gate
# remains tools/ci/scripts/run-secrets-scan.sh.
set -euo pipefail

repo_root="${1:-$(git rev-parse --show-toplevel)}"
expected_version="8.30.1"
command -v gitleaks >/dev/null 2>&1 || { echo "staged_secret_gitleaks_missing:expected=${expected_version}" >&2; exit 1; }
actual_version="$(gitleaks version 2>/dev/null || true)"
[[ "${actual_version}" == "${expected_version}" ]] || { echo "staged_secret_gitleaks_version_mismatch:expected=${expected_version}:actual=${actual_version:-unavailable}" >&2; exit 1; }
exec gitleaks git --staged --config "${repo_root}/.gitleaks.toml" --redact=100 --no-banner \
  "${repo_root}"
