#!/usr/bin/env bash
# Run the repository-local CI fallback gate.
#
# Boundary:
# - This is local fallback evidence when hosted CI or remote publication is
#   unavailable, delayed, or intentionally deferred.
# - It invokes the same reusable owner scripts used by hosted CI projections.
# - It does not claim hosted GitLab/GitHub runner success.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- uv run --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; cd "${repo_root}"; export PYTHONWARNINGS=error

ethos_local_ci_head="$(tools/ci/scripts/require-stable-head.sh capture)"
_ethos_verify_local_ci_head_stability() { tools/ci/scripts/require-stable-head.sh verify "${ethos_local_ci_head}" "tools/ci/scripts/run-local-ci.sh"; }
trap _ethos_verify_local_ci_head_stability EXIT

.venv/bin/nox -s lint
quality_checks=(tools/ci/scripts/run-config-lint.sh tools/ci/scripts/run-json-schema-check.sh tools/ci/scripts/run-shell-lint.sh tools/ci/scripts/run-markdown-lint.sh tools/ci/scripts/run-prose-check.sh tools/ci/scripts/run-import-linter.sh .venv/bin/nox -s dependencies tools/ci/scripts/run-docstring-coverage.sh tools/ci/scripts/run-module-layout.sh tools/ci/scripts/run-product-boundary.sh .venv/bin/nox -s vulnerabilities tools/ci/scripts/run-repository-hygiene.sh tools/ci/scripts/run-secrets-scan.sh tools/ci/scripts/run-ci-template-check.sh tools/ci/scripts/run-format-selection.sh tools/ci/scripts/run-architecture-projection-drift.sh tools/ci/scripts/run-runbook-registry-check.sh)
for check in "${quality_checks[@]}"; do "${check}"; done
.venv/bin/nox -s tests
delivery_checks=(".venv/bin/nox -s install_smoke" tools/ci/scripts/run-release-supply-chain.sh tools/ci/scripts/run-hosted-provider-observation.sh)
for check in "${delivery_checks[@]}"; do "${check}"; done

mkdir -p build/evidence/local-ci
ETHOS_LOCAL_CI_HEAD="${ethos_local_ci_head}" python - <<'PY'
import json, os; from datetime import UTC, datetime; from pathlib import Path
path = Path("build/evidence/local-ci/fallback.json"); payload = {"schema_version": 1, "kind": "ethos_local_ci_fallback_evidence", "verdict": "pass", "state": "passed", "head": os.environ["ETHOS_LOCAL_CI_HEAD"], "command": "tools/ci/scripts/run-local-ci.sh", "generated_at": datetime.now(UTC).isoformat(), "head_stability": "verified_by_exit_trap", "hosted_ci_status_claimed": False, "remote_publication_claimed": False}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps(payload, indent=2, sort_keys=True))
PY
