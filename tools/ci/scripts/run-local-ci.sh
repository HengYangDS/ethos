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

tools/ci/scripts/run-python-lint.sh
tools/ci/scripts/run-config-lint.sh
tools/ci/scripts/run-shell-lint.sh
tools/ci/scripts/run-markdown-lint.sh
tools/ci/scripts/run-import-linter.sh
tools/ci/scripts/run-docstring-coverage.sh
tools/ci/scripts/run-module-layout.sh
tools/ci/scripts/run-bandit.sh
tools/ci/scripts/run-repository-hygiene.sh
tools/ci/scripts/run-secrets-scan.sh
tools/ci/scripts/run-python-tests.sh
