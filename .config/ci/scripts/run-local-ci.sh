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

.config/ci/scripts/run-python-lint.sh
.config/ci/scripts/run-config-lint.sh
.config/ci/scripts/run-shell-lint.sh
.config/ci/scripts/run-markdown-lint.sh
.config/ci/scripts/run-import-linter.sh
.config/ci/scripts/run-docstring-coverage.sh
.config/ci/scripts/run-module-layout.sh
.config/ci/scripts/run-bandit.sh
.config/ci/scripts/run-repository-hygiene.sh
.config/ci/scripts/run-secrets-scan.sh
.config/ci/scripts/run-python-tests.sh
