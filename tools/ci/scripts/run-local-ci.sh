#!/usr/bin/env bash
# Run the repository-local CI fallback gate.
#
# Boundary:
# - This is local fallback evidence when hosted CI or remote publication is
#   unavailable, delayed, or intentionally deferred.
# - It invokes the same reusable owner scripts used by hosted CI projections.
# - It does not claim hosted GitLab/GitHub runner success.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

ethos_local_ci_head="$(tools/ci/scripts/require-stable-head.sh capture)"
_ethos_verify_local_ci_head_stability() {
  tools/ci/scripts/require-stable-head.sh verify \
    "${ethos_local_ci_head}" \
    "tools/ci/scripts/run-local-ci.sh"
}
trap _ethos_verify_local_ci_head_stability EXIT

tools/ci/scripts/run-python-lint.sh
tools/ci/scripts/run-config-lint.sh
tools/ci/scripts/run-json-schema-check.sh
tools/ci/scripts/run-shell-lint.sh
tools/ci/scripts/run-markdown-lint.sh
tools/ci/scripts/run-prose-check.sh
tools/ci/scripts/run-import-linter.sh
tools/ci/scripts/run-dependency-hygiene.sh
tools/ci/scripts/run-docstring-coverage.sh
tools/ci/scripts/run-module-layout.sh
tools/ci/scripts/run-product-boundary.sh
tools/ci/scripts/run-governance-kernel.sh
tools/ci/scripts/run-bandit.sh
tools/ci/scripts/run-python-vulnerability-audit.sh
tools/ci/scripts/run-repository-hygiene.sh
tools/ci/scripts/run-secrets-scan.sh
tools/ci/scripts/run-ci-template-check.sh
tools/ci/scripts/run-format-selection.sh
tools/ci/scripts/run-architecture-projection-drift.sh
tools/ci/scripts/run-runbook-registry-check.sh
tools/ci/scripts/run-mcp-smoke.sh
tools/ci/scripts/run-closeout-evidence-manifest.sh
tools/ci/scripts/run-local-state-audit.sh
tools/ci/scripts/run-release-supply-chain.sh
tools/ci/scripts/run-hosted-provider-observation.sh
tools/ci/scripts/run-python-tests.sh
