#!/usr/bin/env bash
# Bind one Python/uv invocation to the current checkout's semantic runtime homes.
#
# A virtual environment is source-bound: it must never be inherited from another
# checkout. uv's download/build cache is content-addressed acceleration state, so
# callers may supply a host or CI cache explicitly. Neither location is evidence,
# coordination, or authority state.
set -euo pipefail

[[ "${1:-}" != "--" ]] || shift
if [[ "$#" -eq 0 ]]; then
  echo "usage: with-python-runtime.sh -- <command> [args...]" >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"
inherited_runtime_root="${ETHOS_RUNTIME_ROOT:-}"

# The project environment is deliberately not overrideable: a per-checkout
# environment is the boundary that prevents a Work Lane from running another
# checkout's installed source.
export UV_PROJECT_ENVIRONMENT="${repo_root}/build/runtime/venv"

# A CI runner may provide UV_CACHE_DIR directly. Local operators may use the
# ETHOS-specific override; otherwise use host-local XDG state outside the repo.
if [[ -n "${ETHOS_UV_CACHE_DIR:-}" ]]; then
  export UV_CACHE_DIR="${ETHOS_UV_CACHE_DIR}"
elif [[ -n "${UV_CACHE_DIR:-}" ]]; then
  export UV_CACHE_DIR
else
  export UV_CACHE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/ethos/uv"
fi

mkdir -p "${UV_CACHE_DIR}"
export ETHOS_RUNTIME_ROOT="${repo_root}"

# Hooks resolve the checkout interpreter directly so their ordinary fast path
# neither shells through uv nor touches a root `.venv`.  On a fresh checkout
# that interpreter does not exist yet.  Treat that exact, default target as a
# lazy bootstrap request: uv creates the checkout-bound environment and then
# runs the same Python argv.  Explicit ETHOS_PYTHON/PYTHON overrides do not
# match this path and therefore retain their caller-owned semantics.
semantic_python="${UV_PROJECT_ENVIRONMENT}/bin/python"
if [[ "$1" == "${semantic_python}" && ! -x "${semantic_python}" ]]; then
  bootstrap_cache_dir="${UV_CACHE_DIR}"
  if [[ -n "${inherited_runtime_root}" && "${inherited_runtime_root}" != "${repo_root}" ]]; then
    # An outer uv invocation holds its cache lock for the full command. A hook
    # in a different checkout must still materialize that checkout's source
    # environment, so give only this recursive bootstrap a deterministic child
    # namespace beneath the already selected host or CI cache root.
    nested_cache_key="$(printf '%s' "${repo_root}" | cksum | awk '{print $1}')"
    bootstrap_cache_dir="${UV_CACHE_DIR}/nested-bootstrap/${nested_cache_key}"
    mkdir -p "${bootstrap_cache_dir}"
  fi
  exec env UV_CACHE_DIR="${bootstrap_cache_dir}" uv run --group dev python "${@:2}"
fi

# Owner scripts enter through `uv run ... env ETHOS_RUNTIME_BOOTSTRAPPED=1`.
# Their bodies may invoke uv for the tool they own.  A synchronizing outer uv
# process holds the semantic-environment lock until that body exits, which makes
# the inner invocation wait on its own parent.  The marker is the explicit
# handoff boundary: preserve its command and dependency selection, but keep the
# outer runner non-synchronizing so the body owns any required sync itself.
runtime_command=("$@")
if [[ "${runtime_command[0]}" == "uv" && "${runtime_command[1]:-}" == "run" ]]; then
  owner_script_handoff="false"
  no_sync_requested="false"
  for ((argument_index = 2; argument_index < ${#runtime_command[@]}; argument_index++)); do
    if [[ "${runtime_command[argument_index]}" == "--no-sync" ]]; then
      no_sync_requested="true"
    fi
    if [[ "${runtime_command[argument_index]}" == "env" ]]; then
      for ((environment_index = argument_index + 1; environment_index < ${#runtime_command[@]}; environment_index++)); do
        environment_assignment="${runtime_command[environment_index]}"
        if [[ "${environment_assignment}" != *=* ]]; then
          break
        fi
        if [[ "${environment_assignment}" == "ETHOS_RUNTIME_BOOTSTRAPPED=1" ]]; then
          owner_script_handoff="true"
        fi
      done
    fi
  done
  if [[ "${owner_script_handoff}" == "true" && "${no_sync_requested}" != "true" ]]; then
    exec uv run --no-sync "${runtime_command[@]:2}"
  fi
fi

exec "$@"
