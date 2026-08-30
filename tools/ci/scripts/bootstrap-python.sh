#!/usr/bin/env bash
# Synchronize the repository-local Python and OpenSpec runtimes from locked inputs.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"
export UV_PROJECT_ENVIRONMENT="${repo_root}/.venv"

case "$(uname -s)" in
Linux)
	missing_packages=()
	if ! command -v git >/dev/null 2>&1; then missing_packages+=(git); fi
	if ! command -v ldconfig >/dev/null 2>&1 ||
		! ldconfig -p 2>/dev/null | grep -q 'libatomic\.so\.1'; then
		missing_packages+=(libatomic1)
	fi
	if ((${#missing_packages[@]})); then
		if ! command -v apt-get >/dev/null 2>&1; then
			printf 'missing Linux prerequisites and apt-get is unavailable: %s\n' "${missing_packages[*]}" >&2
			exit 1
		fi
		apt-get update
		apt-get install -y --no-install-recommends "${missing_packages[@]}"
	fi
	;;
Darwin)
	if ! command -v git >/dev/null 2>&1; then
		echo "Git is required to bootstrap ETHOS on Darwin" >&2
		exit 1
	fi
	;;
*)
	printf 'unsupported Python bootstrap operating system: %s\n' "$(uname -s)" >&2
	exit 1
	;;
esac

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
required_uv="$(
	"${script_dir}/with-python-runtime.sh" -- uv run --no-sync python - <<'PY_VERSION'
import re
import tomllib
from pathlib import Path

project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
requirement = next(
    value for value in project["dependency-groups"]["dev"] if value.startswith("uv>=")
)
match = re.fullmatch(r"uv>=(\d+\.\d+\.\d+)", requirement)
if match is None:
    raise SystemExit("pyproject.toml must declare one exact uv minimum")
print(match.group(1))
PY_VERSION
)"
actual_uv="$(uv --version | awk '{print $2}')"
if [[ "${actual_uv}" != "${required_uv}" ]]; then
	printf 'uv version mismatch: expected %s, observed %s\n' "${required_uv}" "${actual_uv}" >&2
	exit 1
fi

# The OpenSpec shim execs npx. Hosted Python images do not supply Node, and
# this runner's Debian mirror can stall during apt installation. Reuse the
# checksum-pinned Node archive installer so every hosted job has node/npm/npx
# without a Debian package dependency.
if ! command -v npx >/dev/null 2>&1; then
	"${script_dir}/install-node.sh"
fi
uv --version
if [[ ! -x "${repo_root}/node_modules/.bin/openspec" ]]; then npm ci --ignore-scripts; fi
"${repo_root}/node_modules/.bin/openspec" --version
uv sync --locked --group dev
