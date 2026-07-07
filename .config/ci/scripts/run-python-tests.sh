#!/usr/bin/env bash
# Run the Python trust-bearing test gate with coverage.
#
# This is the owner script for the product test gate. Hosted CI and ETHOS proof
# call this script instead of duplicating pytest/coverage policy inline.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

coverage_config_dir=".config/checks/coverage"
evidence_root="${ETHOS_TEST_EVIDENCE_DIR:-build/evidence/quality/tests}"
coverage_evidence_dir="${evidence_root}/coverage"
pytest_evidence_dir="${evidence_root}/pytest"
pytest_tmp_dir="${ETHOS_TEST_BASETEMP:-${TMPDIR:-/tmp}/ethos-pytest-${USER:-user}-$$}"
mkdir -p "${coverage_evidence_dir}" "${pytest_evidence_dir}" "${pytest_tmp_dir}"
export COVERAGE_FILE="${coverage_evidence_dir}/.coverage"

workers="${ETHOS_TEST_WORKERS:-auto}"
durations="${ETHOS_TEST_DURATIONS:-20}"
pytest_args=(
  --cov-config="${coverage_config_dir}/coverage.ini"
  --cov=ethos
  --cov=ethos_core
  --cov-report=term-missing
  --cov-report="xml:${coverage_evidence_dir}/coverage.xml"
  --cov-fail-under=100
  --junitxml="${pytest_evidence_dir}/junit.xml"
  --basetemp="${pytest_tmp_dir}"
  --durations="${durations}"
  --dist=loadscope
  tests/unit
  tests/architecture
  -q
)

if [[ "${workers}" != "1" && "${workers}" != "serial" ]]; then
  pytest_args=( -n "${workers}" "${pytest_args[@]}" )
fi

# --all-packages installs every workspace member's runtime deps (not just the root
# project + dev group), so tests that import a package dependency (e.g. defusedxml
# via ethos) resolve in CI's clean environment. Mirrors the ethos:types invocation.
uv run --all-packages --group dev pytest "${pytest_args[@]}"
