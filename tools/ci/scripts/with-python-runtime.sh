#!/usr/bin/env bash
# Bind one Python/uv invocation to the current checkout's semantic runtime homes.
#
# A virtual environment is source-bound: it must never be inherited from another
# checkout. uv's download/build cache is content-addressed acceleration state, so
# callers may supply a host or CI cache explicitly. Neither location is evidence,
# coordination, or authority state.
set -euo pipefail

if [[ "${1:-}" == "--" ]]; then
  shift
fi
if [[ "$#" -eq 0 ]]; then
  echo "usage: with-python-runtime.sh -- <command> [args...]" >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

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

# Hooks resolve the checkout interpreter directly so their ordinary fast path
# neither shells through uv nor touches a root `.venv`.  On a fresh checkout
# that interpreter does not exist yet.  Treat that exact, default target as a
# lazy bootstrap request: uv creates the checkout-bound environment and then
# runs the same Python argv.  Explicit ETHOS_PYTHON/PYTHON overrides do not
# match this path and therefore retain their caller-owned semantics.
semantic_python="${UV_PROJECT_ENVIRONMENT}/bin/python"
if [[ "$1" == "${semantic_python}" && ! -x "${semantic_python}" ]]; then
  exec uv run --group dev python "${@:2}"
fi

exec "$@"
