#!/usr/bin/env bash
# Run the Python trust-bearing test gate with coverage.
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then exec "${script_dir}/with-python-runtime.sh" -- uv run --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"; fi
run_as_uid="${ETHOS_TEST_RUN_AS_UID:-}"; run_as_gid="${ETHOS_TEST_RUN_AS_GID:-}"
repo_root_from_script="$(cd "${script_dir}/../../.." && pwd)"
export GIT_CONFIG_COUNT="${GIT_CONFIG_COUNT:-0}"; git_config_count="${GIT_CONFIG_COUNT}"
if ! [[ "${git_config_count}" =~ ^[0-9]+$ ]]; then echo "GIT_CONFIG_COUNT must be a non-negative integer" >&2; exit 2; fi
if [[ -n "${run_as_uid}" || -n "${run_as_gid}" ]]; then
  for git_safe_directory in "${repo_root_from_script}" "${repo_root_from_script}/.git"; do
    git_config_safe_directory_index="${git_config_count}"
    export GIT_CONFIG_KEY_"${git_config_safe_directory_index}"=safe.directory
    export GIT_CONFIG_VALUE_"${git_config_safe_directory_index}"="${git_safe_directory}"
    git_config_count="$((git_config_count + 1))"
  done
  export GIT_CONFIG_COUNT="${git_config_count}"
fi
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || printf '%s\n' "${repo_root_from_script}")"; cd "${repo_root}"
ethos_python_test_head="$(tools/ci/scripts/require-stable-head.sh capture)"
_ethos_verify_python_test_head_stability() { tools/ci/scripts/require-stable-head.sh verify "${ethos_python_test_head}" "tools/ci/scripts/run-python-tests.sh"; }
coverage_config_dir=".config/checks/coverage"; coverage_policy_path="${coverage_config_dir}/policy.toml"; pytest_config_path=".config/checks/pytest/pytest.ini"
evidence_root="${ETHOS_TEST_EVIDENCE_DIR:-build/evidence/quality/tests}"; coverage_evidence_dir="${evidence_root}/coverage"; pytest_evidence_dir="${evidence_root}/pytest"
coverage_head_path="${coverage_evidence_dir}/head.txt"
coverage_lock_dir="${coverage_evidence_dir}/.write.lock"; coverage_lock_owner_path="${coverage_lock_dir}/owner.pid"; coverage_lock_wait_seconds="${ETHOS_COVERAGE_LOCK_WAIT_SECONDS:-30}"
pytest_tmp_dir="${ETHOS_TEST_BASETEMP:-${TMPDIR:-/tmp}/ethos-pytest-${USER:-user}-$$}"; workers="${ETHOS_TEST_WORKERS:-8}"; durations="${ETHOS_TEST_DURATIONS:-20}"; shards="${ETHOS_TEST_SHARDS:-1}"
timeout_seconds="${ETHOS_TEST_TIMEOUT_SECONDS:-}"; timeout_method="${ETHOS_TEST_TIMEOUT_METHOD:-}"
if [[ -n "${timeout_seconds}" || -n "${timeout_method}" ]]; then
  if [[ -z "${timeout_seconds}" || -z "${timeout_method}" ]]; then echo "ETHOS_TEST_TIMEOUT_SECONDS and ETHOS_TEST_TIMEOUT_METHOD must be set together" >&2; exit 2; fi
  if ! [[ "${timeout_seconds}" =~ ^[1-9][0-9]*$ ]]; then echo "ETHOS_TEST_TIMEOUT_SECONDS must be a positive integer" >&2; exit 2; fi
  case "${timeout_method}" in signal|thread) ;; *) echo "ETHOS_TEST_TIMEOUT_METHOD must be signal or thread" >&2; exit 2 ;; esac
fi
pytest_identity_prefix=(); identity_runtime_dir=""
if [[ -n "${run_as_uid}" || -n "${run_as_gid}" ]]; then
  if [[ -z "${run_as_uid}" || -z "${run_as_gid}" ]]; then echo "ETHOS_TEST_RUN_AS_UID and ETHOS_TEST_RUN_AS_GID must be set together" >&2; exit 2; fi
  if ! [[ "${run_as_uid}" =~ ^[1-9][0-9]*$ && "${run_as_gid}" =~ ^[1-9][0-9]*$ ]]; then echo "ETHOS_TEST_RUN_AS_UID and ETHOS_TEST_RUN_AS_GID must be positive decimal integers" >&2; exit 2; fi
  if ! command -v setpriv >/dev/null 2>&1; then echo "setpriv is required for ETHOS_TEST_RUN_AS_UID/ETHOS_TEST_RUN_AS_GID" >&2; exit 2; fi
  if [[ "$(id -u)" != "0" ]]; then echo "ETHOS_TEST_RUN_AS_UID/ETHOS_TEST_RUN_AS_GID require a root launcher" >&2; exit 2; fi
  pytest_identity_prefix=(setpriv "--reuid=${run_as_uid}" "--regid=${run_as_gid}" --clear-groups)
  identity_tmp_root="${TMPDIR:-/tmp}"; identity_tmp_root="${identity_tmp_root%/}"
  identity_runtime_dir="${identity_tmp_root}/ethos-test-identity-${run_as_uid}-${run_as_gid}-$$"
fi
if ! [[ "${coverage_lock_wait_seconds}" =~ ^[0-9]+$ ]]; then echo "ETHOS_COVERAGE_LOCK_WAIT_SECONDS must be a non-negative integer" >&2; exit 2; fi
if [[ "${shards}" != "1" && "${shards}" != "serial" ]] && { ! [[ "${shards}" =~ ^[0-9]+$ ]] || [[ "${shards}" -lt 1 ]]; }; then echo "ETHOS_TEST_SHARDS must be a positive integer" >&2; exit 2; fi
ethos_python="${ETHOS_PYTHON:-${PYTHON:-${UV_PROJECT_ENVIRONMENT}/bin/python}}"
export UV_PROJECT_ENVIRONMENT=".venv"
export COVERAGE_FILE="${coverage_evidence_dir}/.coverage" RUFF_CACHE_DIR="${RUFF_CACHE_DIR:-${repo_root}/build/runtime/tool-cache/ruff}"
if [[ "$#" -gt 1 || ( "$#" -eq 1 && "$1" != "--enforce-coverage-floor" ) ]]; then
  echo "usage: $0 [--enforce-coverage-floor]" >&2
  exit 2
fi
coverage_floor_only="false"
if [[ "${1:-}" == "--enforce-coverage-floor" ]]; then coverage_floor_only="true"; fi
coverage_hard_floor="$(
  "${ethos_python}" - "${coverage_policy_path}" <<'PY'
import sys, tomllib
from pathlib import Path
value = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("current_hard_floor")
if not isinstance(value, int | float): raise SystemExit("coverage policy current_hard_floor must be numeric")
print(f"{value:g}")
PY
)"
if [[ "${#pytest_identity_prefix[@]}" -gt 0 ]]; then
  export HOME="${identity_runtime_dir}/home" XDG_CACHE_HOME="${identity_runtime_dir}/home/.cache" PYTHONDONTWRITEBYTECODE=1
  identity_writable_paths=(build "${coverage_evidence_dir}" "${pytest_evidence_dir}" "${pytest_tmp_dir}" "${identity_runtime_dir}")
  for identity_writable_path in "${identity_writable_paths[@]}"; do
    case "${identity_writable_path}" in build|build/*|"${repo_root}"/build|"${repo_root}"/build/*|"${identity_tmp_root}"/*) ;; *) echo "unprivileged test path escapes build or TMPDIR: ${identity_writable_path}" >&2; exit 2 ;; esac
  done
  mkdir -p "${identity_writable_paths[@]}" "${HOME}"
  chown -R "${run_as_uid}:${run_as_gid}" "${identity_writable_paths[@]}" "${HOME}"
else
  mkdir -p "${coverage_evidence_dir}" "${pytest_evidence_dir}" "${pytest_tmp_dir}"
fi
if [[ "${#pytest_identity_prefix[@]}" -gt 0 ]]; then unset ETHOS_TEST_RUN_AS_UID ETHOS_TEST_RUN_AS_GID; fi
coverage_lock_acquired="false"; coverage_lock_invalid_reclaim_attempted="false"; sharded_mode="false"
if [[ "${shards}" != "1" && "${shards}" != "serial" ]]; then sharded_mode="true"; fi
# Preserve caller-owned Git overlays while disabling only fsmonitor for test subprocesses.
git_config_fsmonitor_index="${git_config_count}"
export GIT_CONFIG_KEY_"${git_config_fsmonitor_index}"=core.fsmonitor
export GIT_CONFIG_VALUE_"${git_config_fsmonitor_index}"=false
export GIT_CONFIG_COUNT="$((git_config_count + 1))"
cleanup_source_bytecode_caches() {
  find src -type d -name "__pycache__" -prune -exec rm -rf {} +
  find src -depth -type d -empty -delete
}
cleanup_denied_runtime_residue() {
  rm -rf .pytest_cache .ruff_cache build/runtime/gitlab-ci-local
  cleanup_source_bytecode_caches
}
cleanup_root_coverage_artifacts() { rm -f .coverage .coverage.* coverage.xml junit.xml; }
cleanup_identity_runtime() { if [[ -n "${identity_runtime_dir}" ]]; then rm -rf "${identity_runtime_dir}"; fi; }
restore_root_runtime_ownership() {
  if [[ "${#pytest_identity_prefix[@]}" -gt 0 ]]; then
    for identity_restore_path in build "${pytest_tmp_dir}"; do
      if [[ -e "${identity_restore_path}" || -L "${identity_restore_path}" ]]; then chown -R 0:0 "${identity_restore_path}"; fi
    done
  fi
}
release_coverage_lock() { if [[ "${coverage_lock_acquired}" == "true" ]]; then rm -f "${coverage_lock_owner_path}"; rmdir "${coverage_lock_dir}" 2>/dev/null || true; fi; }
release_coverage_lock_and_verify_head() { release_coverage_lock; _ethos_verify_python_test_head_stability; }
cleanup_and_release() {
  cleanup_denied_runtime_residue; cleanup_root_coverage_artifacts; release_coverage_lock; cleanup_identity_runtime; restore_root_runtime_ownership; _ethos_verify_python_test_head_stability
}
# coverage evidence writes are serialized; only a PID/start-fingerprint-proven dead owner is reclaimed.
coverage_lock_process_start() { local owner_pid="$1"; ps -o lstart= -p "${owner_pid}" 2>/dev/null | tr -s ' ' | sed 's/^ //' || true; }
coverage_lock_owner_is_dead() {
  local owner_pid="" owner_started_at="" current_started_at=""
  [[ -f "${coverage_lock_owner_path}" ]] || return 1
  IFS=$'\t' read -r owner_pid owner_started_at < "${coverage_lock_owner_path}" || return 1
  [[ "${owner_pid}" =~ ^[1-9][0-9]*$ && -n "${owner_started_at}" ]] || return 1
  if ! kill -0 "${owner_pid}" 2>/dev/null; then return 0; fi
  current_started_at="$(coverage_lock_process_start "${owner_pid}")"; [[ -n "${current_started_at}" && "${current_started_at}" != "${owner_started_at}" ]]
}
coverage_lock_owner_is_invalid() { local owner_pid="" owner_started_at="" owner_extra=""; [[ -f "${coverage_lock_owner_path}" ]] || return 0; IFS=$'\t' read -r owner_pid owner_started_at owner_extra < "${coverage_lock_owner_path}" || return 0; [[ -z "${owner_extra}" && "${owner_pid}" =~ ^[1-9][0-9]*$ && -n "${owner_started_at}" ]] || return 0; return 1; }
reclaim_stale_coverage_lock() {
  coverage_lock_owner_is_dead || return 1
  rm -f "${coverage_lock_owner_path}"
  if rmdir "${coverage_lock_dir}" 2>/dev/null; then echo "reclaimed stale coverage evidence lock: ${coverage_lock_dir}" >&2; return 0; fi
  return 1
}
coverage_lock_wait_started="${SECONDS}"
while ! mkdir "${coverage_lock_dir}" 2>/dev/null; do
  if reclaim_stale_coverage_lock; then continue; fi
  if (( SECONDS - coverage_lock_wait_started >= coverage_lock_wait_seconds )); then
    if [[ "${coverage_lock_invalid_reclaim_attempted}" == "false" ]] && coverage_lock_owner_is_invalid; then coverage_lock_invalid_reclaim_attempted="true"; rm -f "${coverage_lock_owner_path}"; if rmdir "${coverage_lock_dir}" 2>/dev/null; then echo "reclaimed invalid coverage evidence lock: ${coverage_lock_dir}" >&2; coverage_lock_wait_started="${SECONDS}"; continue; fi; fi
    owner_metadata="unknown"; if [[ -f "${coverage_lock_owner_path}" ]]; then IFS= read -r owner_metadata < "${coverage_lock_owner_path}" || owner_metadata="unreadable"; fi
    echo "coverage evidence lock remained unavailable after ${coverage_lock_wait_seconds}s: ${coverage_lock_dir} (owner=${owner_metadata})" >&2; exit 1
  fi
  echo "waiting for coverage evidence lock: ${coverage_lock_dir}" >&2; sleep 1
done
coverage_lock_acquired="true"; coverage_lock_owner_started_at="$(coverage_lock_process_start "$$")"
if [[ -z "${coverage_lock_owner_started_at}" ]] || ! printf '%s\t%s\n' "$$" "${coverage_lock_owner_started_at}" > "${coverage_lock_owner_path}"; then coverage_lock_acquired="false"; rmdir "${coverage_lock_dir}" 2>/dev/null || true; echo "failed to record coverage evidence lock owner: ${coverage_lock_dir}" >&2; exit 1; fi
if [[ "${coverage_floor_only}" == "true" ]]; then
  trap release_coverage_lock_and_verify_head EXIT
  if [[ ! -s "${COVERAGE_FILE}" || ! -f "${coverage_head_path}" ]] ||
    [[ "$(cat "${coverage_head_path}")" != "${ethos_python_test_head}" ]]; then
    echo "coverage evidence is missing or stale for ${ethos_python_test_head}" >&2
    exit 1
  fi
  "${ethos_python}" -m coverage report \
    --data-file="${COVERAGE_FILE}" \
    --fail-under="${coverage_hard_floor}"
  exit 0
fi
cleanup_denied_runtime_residue; cleanup_root_coverage_artifacts; trap cleanup_and_release EXIT
shard_state_dir="${pytest_evidence_dir}/shards"; shard_head_path="${shard_state_dir}/head.txt"; shard_plan_key="${ethos_python_test_head}:shards=${shards}"
if [[ "${sharded_mode}" == "true" ]]; then
  mkdir -p "${shard_state_dir}"
  if [[ ! -f "${shard_head_path}" ]] || [[ "$(cat "${shard_head_path}")" != "${shard_plan_key}" ]]; then rm -f "${COVERAGE_FILE}" "${COVERAGE_FILE}".* "${coverage_evidence_dir}/coverage.xml" "${pytest_evidence_dir}"/junit*.xml; rm -rf "${shard_state_dir}"; mkdir -p "${shard_state_dir}"; printf '%s\n' "${shard_plan_key}" > "${shard_head_path}"; fi
else
  rm -f "${COVERAGE_FILE}" "${COVERAGE_FILE}".*; rm -f "${coverage_evidence_dir}/coverage.xml"; rm -f "${pytest_evidence_dir}/junit.xml"
fi
pytest_targets=(tests/unit tests/architecture)
pytest_common_args=(-c "${pytest_config_path}" -W error --rootdir=. --cov-config="${coverage_config_dir}/coverage.ini" --cov=ethos --basetemp="${pytest_tmp_dir}" --durations="${durations}" --dist=loadscope)
if [[ -n "${timeout_seconds}" ]]; then pytest_common_args+=(--timeout="${timeout_seconds}" --timeout-method="${timeout_method}"); fi
pytest_junit_arg=(--junitxml="${pytest_evidence_dir}/junit.xml")
pytest_report_args=(--cov-report=term-missing --cov-report="xml:${coverage_evidence_dir}/coverage.xml" --cov-fail-under=0)
pytest_runner=("${ethos_python}" -m pytest); coverage_runner=("${ethos_python}" -m coverage)
if ! "${ethos_python}" -m pytest --version >/dev/null 2>&1; then pytest_runner=(uv run --group dev pytest); coverage_runner=(uv run --group dev coverage); fi
if [[ "${workers}" != "1" && "${workers}" != "serial" ]]; then pytest_common_args=(-n "${workers}" "${pytest_common_args[@]}"); fi
export GIT_CONFIG_GLOBAL="${GIT_CONFIG_GLOBAL:-/dev/null}" GIT_CONFIG_NOSYSTEM="${GIT_CONFIG_NOSYSTEM:-1}"
run_pytest() {
  if [[ "${#pytest_identity_prefix[@]}" -gt 0 ]]; then
    env -u ETHOS_ACTOR "${pytest_identity_prefix[@]}" "${pytest_runner[@]}" "$@"
  else
    env -u ETHOS_ACTOR "${pytest_runner[@]}" "$@"
  fi
}
run_coverage() { "${coverage_runner[@]}" "$@"; }
if [[ "${sharded_mode}" != "true" ]]; then
  run_pytest "${pytest_common_args[@]}" "${pytest_junit_arg[@]}" "${pytest_report_args[@]}" "${pytest_targets[@]}" -q
else
  nodeids_path="${pytest_evidence_dir}/nodeids.txt"
  run_pytest --collect-only -q -c "${pytest_config_path}" --rootdir=. "${pytest_targets[@]}" > "${nodeids_path}"
  "${ethos_python}" - "${nodeids_path}" "${pytest_evidence_dir}" "${shards}" <<'PY'
import sys
from pathlib import Path
nodeids_path, shard_dir, shards = Path(sys.argv[1]), Path(sys.argv[2]) / "shards", int(sys.argv[3])
nodeids = [line.strip() for line in nodeids_path.read_text(encoding="utf-8").splitlines() if line.startswith("tests/") and "::" in line]
if not nodeids: raise SystemExit("pytest collect-only produced no nodeids")
shard_dir.mkdir(parents=True, exist_ok=True)
for shard_index in range(shards):
    shard_nodeids = nodeids[shard_index::shards]
    (shard_dir / f"shard-{shard_index + 1}.txt").write_text("\n".join(shard_nodeids) + ("\n" if shard_nodeids else ""), encoding="utf-8")
PY
  for shard_index in $(seq 1 "${shards}"); do
    shard_file="${pytest_evidence_dir}/shards/shard-${shard_index}.txt"; if [[ ! -s "${shard_file}" ]]; then continue; fi
    shard_nodeids=(); while IFS= read -r shard_nodeid; do if [[ -n "${shard_nodeid}" ]]; then shard_nodeids+=("${shard_nodeid}"); fi; done < "${shard_file}"
    shard_coverage_file="${coverage_evidence_dir}/.coverage.shard-${shard_index}"; shard_junit="${pytest_evidence_dir}/junit-shard-${shard_index}.xml"; shard_passed_marker="${pytest_evidence_dir}/shards/shard-${shard_index}.passed"
    if [[ -s "${shard_coverage_file}" && -f "${shard_passed_marker}" && "$(cat "${shard_passed_marker}")" == "${shard_plan_key}" ]]; then echo "reusing completed pytest shard ${shard_index}/${shards}" >&2; continue; fi
    rm -f "${shard_coverage_file}" "${shard_junit}" "${shard_passed_marker}"
    COVERAGE_FILE="${shard_coverage_file}" run_pytest "${pytest_common_args[@]}" --cov-report= --cov-fail-under=0 --junitxml="${shard_junit}" "${shard_nodeids[@]}" -q
    printf '%s\n' "${shard_plan_key}" > "${shard_passed_marker}"
  done
  for shard_index in $(seq 1 "${shards}"); do
    shard_file="${pytest_evidence_dir}/shards/shard-${shard_index}.txt"; shard_coverage_file="${coverage_evidence_dir}/.coverage.shard-${shard_index}"; shard_passed_marker="${pytest_evidence_dir}/shards/shard-${shard_index}.passed"
    if [[ -s "${shard_file}" && ! ( -s "${shard_coverage_file}" && -f "${shard_passed_marker}" && "$(cat "${shard_passed_marker}")" == "${shard_plan_key}" ) ]]; then echo "pytest shard ${shard_index}/${shards} has no completed coverage evidence" >&2; exit 1; fi
  done
  run_coverage combine --data-file="${COVERAGE_FILE}" "${coverage_evidence_dir}"
  run_coverage xml --data-file="${COVERAGE_FILE}" -o "${coverage_evidence_dir}/coverage.xml"
  run_coverage report --data-file="${COVERAGE_FILE}" --fail-under=0
fi
printf '%s\n' "${ethos_python_test_head}" > "${coverage_head_path}"
