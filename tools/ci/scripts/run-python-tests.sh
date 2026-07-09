#!/usr/bin/env bash
# Run the Python trust-bearing test gate with coverage.
#
# This is the owner script for the product test gate. Hosted CI and ETHOS proof
# call this script instead of duplicating pytest/coverage policy inline.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

ethos_python_test_head="$(tools/ci/scripts/require-stable-head.sh capture)"
_ethos_verify_python_test_head_stability() {
  tools/ci/scripts/require-stable-head.sh verify \
    "${ethos_python_test_head}" \
    "tools/ci/scripts/run-python-tests.sh"
}

coverage_config_dir=".config/checks/coverage"
coverage_policy_path="${coverage_config_dir}/policy.toml"
pytest_config_path=".config/checks/pytest/pytest.ini"
evidence_root="${ETHOS_TEST_EVIDENCE_DIR:-build/evidence/quality/tests}"
coverage_evidence_dir="${evidence_root}/coverage"
pytest_evidence_dir="${evidence_root}/pytest"
coverage_lock_dir="${coverage_evidence_dir}/.write.lock"
pytest_tmp_dir="${ETHOS_TEST_BASETEMP:-${TMPDIR:-/tmp}/ethos-pytest-${USER:-user}-$$}"
ethos_python="${ETHOS_PYTHON:-${PYTHON:-}}"
if [[ -z "${ethos_python}" && -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
  ethos_python="${VIRTUAL_ENV}/bin/python"
fi
if [[ -z "${ethos_python}" && -x "${repo_root}/.venv/bin/python" ]]; then
  ethos_python="${repo_root}/.venv/bin/python"
fi
if [[ -z "${ethos_python}" ]]; then
  ethos_python="python3"
fi
mkdir -p "${coverage_evidence_dir}" "${pytest_evidence_dir}" "${pytest_tmp_dir}"
export COVERAGE_FILE="${coverage_evidence_dir}/.coverage"
coverage_lock_acquired="false"

cleanup_denied_runtime_residue() {
  # These homes are explicitly denied by the generated-artifact topology. They
  # are ignored local residue, never repository truth; clearing them before the
  # trust-bearing test gate keeps stale host state from deciding product tests.
  rm -rf .pytest_cache .ruff_cache
  rm -rf build/runtime/gitlab-ci-local
}

cleanup_root_coverage_artifacts() {
  rm -f .coverage .coverage.*
  rm -f coverage.xml junit.xml
}

release_coverage_lock() {
  if [[ "${coverage_lock_acquired}" == "true" ]]; then
    rmdir "${coverage_lock_dir}" 2>/dev/null || true
  fi
}

cleanup_and_release() {
  cleanup_root_coverage_artifacts
  release_coverage_lock
  _ethos_verify_python_test_head_stability
}

# The latest coverage XML and pytest-cov SQLite shards are one generated evidence
# boundary. Concurrent proof/local-ci runs must not clean or combine the same files
# while another run is writing them; coverage evidence writes are serialized here.
while ! mkdir "${coverage_lock_dir}" 2>/dev/null; do
  echo "waiting for coverage evidence lock: ${coverage_lock_dir}" >&2
  sleep 1
done
coverage_lock_acquired="true"

# Start each trust-bearing test run from a clean generated evidence boundary.
# pytest-cov and xdist create SQLite shards next to COVERAGE_FILE; older or
# interrupted local runs may also leave root `.coverage*` files behind. Stale
# shards can corrupt the combined report, and root coverage files violate the
# generated-artifact topology before tests reach the real product assertions.
# These files are ignored local evidence, not repository truth.
cleanup_denied_runtime_residue
cleanup_root_coverage_artifacts
trap cleanup_and_release EXIT
rm -f "${COVERAGE_FILE}" "${COVERAGE_FILE}".*
rm -f "${coverage_evidence_dir}/coverage.xml"
rm -f "${pytest_evidence_dir}/junit.xml"

coverage_hard_floor="$(
  "${ethos_python}" - "${coverage_policy_path}" <<'PY'
import sys
import tomllib
from pathlib import Path

policy = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
value = policy.get("current_hard_floor")
if not isinstance(value, int | float):
    raise SystemExit("coverage policy current_hard_floor must be numeric")
print(f"{value:g}")
PY
)"
workers="${ETHOS_TEST_WORKERS:-8}"
durations="${ETHOS_TEST_DURATIONS:-20}"
pytest_args=(
  -c "${pytest_config_path}"
  --rootdir=.
  --cov-config="${coverage_config_dir}/coverage.ini"
  --cov=ethos
  --cov=ethos_core
  --cov-report=term-missing
  --cov-report="xml:${coverage_evidence_dir}/coverage.xml"
  "--cov-fail-under=${coverage_hard_floor}"
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

# In a prepared product toolchain (for example an outer `uv run --package ethos`
# proof), reuse the active interpreter instead of recursively invoking `uv run`;
# nested environment sync is host-sensitive and can terminate the proof runner
# before pytest emits machine evidence. Clean CI environments still fall back to
# `uv run --all-packages --group dev` so workspace runtime dependencies are
# installed before the test gate.
if "${ethos_python}" -m pytest --version >/dev/null 2>&1; then
  "${ethos_python}" -m pytest "${pytest_args[@]}"
else
  uv run --all-packages --group dev pytest "${pytest_args[@]}"
fi
