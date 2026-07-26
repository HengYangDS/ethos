#!/usr/bin/env bash
# Bind one Python/uv invocation to this checkout's semantic runtime homes.
set -euo pipefail
[[ "${1:-}" != "--" ]] || shift
if [[ "$#" -eq 0 ]]; then echo "usage: with-python-runtime.sh -- <command> [args...]" >&2; exit 2; fi
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; cd "${repo_root}"; inherited_runtime_root="${ETHOS_RUNTIME_ROOT:-}"
bootstrap_bin="${repo_root}/build/runtime/tool-cache/uv-bootstrap/bin"
if [[ -x "${bootstrap_bin}/uv" ]]; then export PATH="${bootstrap_bin}:${PATH}"; fi
export UV_PROJECT_ENVIRONMENT="${repo_root}/build/runtime/venv"; unset VIRTUAL_ENV
if [[ -n "${ETHOS_UV_CACHE_DIR:-}" ]]; then export UV_CACHE_DIR="${ETHOS_UV_CACHE_DIR}"; elif [[ -n "${UV_CACHE_DIR:-}" ]]; then export UV_CACHE_DIR; else export UV_CACHE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/ethos/uv"; fi
# Keep a caller-owned relative cache bound to its outer runtime when a nested checkout takes over.
if [[ "${UV_CACHE_DIR}" != /* ]]; then cache_owner_root="${repo_root}"; if [[ -n "${inherited_runtime_root}" && "${inherited_runtime_root}" != "${repo_root}" ]]; then cache_owner_root="${inherited_runtime_root}"; fi; export UV_CACHE_DIR="${cache_owner_root}/${UV_CACHE_DIR}"; fi
mkdir -p "${UV_CACHE_DIR}"; export ETHOS_RUNTIME_ROOT="${repo_root}"
# Bootstrap only the default checkout interpreter; explicit Python overrides remain caller-owned.
semantic_python="${UV_PROJECT_ENVIRONMENT}/bin/python"; if [[ "$1" == "${semantic_python}" ]]; then
  if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" == "1" && -x "${semantic_python}" && -f "${UV_PROJECT_ENVIRONMENT}/pyvenv.cfg" ]]; then exec "$@"; fi
  if [[ -x "${semantic_python}" && -f "${UV_PROJECT_ENVIRONMENT}/pyvenv.cfg" && ! -f "${repo_root}/pyproject.toml" ]]; then exec "$@"; fi
  if [[ -x "${semantic_python}" ]] && uv sync --locked --all-packages --group dev --check >/dev/null 2>&1; then exec "$@"; fi
  bootstrap_cache_dir="${UV_CACHE_DIR}"
  if [[ -n "${inherited_runtime_root}" && "${inherited_runtime_root}" != "${repo_root}" ]]; then nested_cache_key="$(printf '%s' "${repo_root}" | cksum | awk '{print $1}')"; bootstrap_cache_dir="${UV_CACHE_DIR}/nested-bootstrap/${nested_cache_key}"; mkdir -p "${bootstrap_cache_dir}"; fi
  exec env UV_CACHE_DIR="${bootstrap_cache_dir}" uv run --locked --all-packages --group dev python "${@:2}"
fi

# Prevent an owner-script handoff from recursively waiting on its outer uv sync lock.
runtime_command=("$@")
if [[ "${runtime_command[0]}" == "uv" && "${runtime_command[1]:-}" == "run" ]]; then
  owner_script_handoff="false"; no_sync_requested="false"
  for ((argument_index = 2; argument_index < ${#runtime_command[@]}; argument_index++)); do
    if [[ "${runtime_command[argument_index]}" == "--no-sync" ]]; then no_sync_requested="true"; fi
    if [[ "${runtime_command[argument_index]}" == "env" ]]; then
      for ((environment_index = argument_index + 1; environment_index < ${#runtime_command[@]}; environment_index++)); do environment_assignment="${runtime_command[environment_index]}"; if [[ "${environment_assignment}" != *=* ]]; then break; fi; if [[ "${environment_assignment}" == "ETHOS_RUNTIME_BOOTSTRAPPED=1" ]]; then owner_script_handoff="true"; fi; done
    fi
  done
  if [[ "${owner_script_handoff}" == "true" && "${no_sync_requested}" != "true" ]]; then exec uv run --no-sync "${runtime_command[@]:2}"; fi
fi
exec "$@"
