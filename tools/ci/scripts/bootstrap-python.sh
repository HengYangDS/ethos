#!/usr/bin/env bash
# Synchronize the repository-local Python and OpenSpec runtimes from locked inputs.
set -euo pipefail

if (($#)); then
	if [[ "$1" != -- || $# -lt 2 || $$ != 1 || ${EUID} != 0 ||
		${CI_PROJECT_DIR:-} != /* || ${CI_PROJECT_DIR:-} == / ||
		! -d ${CI_PROJECT_DIR:-}/.git || -L ${CI_PROJECT_DIR:-} ]]; then
		echo 'container_job_entrypoint_required' >&2
		exit 2
	fi
	shift
	cd -- "${CI_PROJECT_DIR}"
	[[ "$(pwd -P)" == "${CI_PROJECT_DIR}" ]] || exit 2
	export HOME="${CI_PROJECT_DIR}/build/runtime/work/ci-home"
	export XDG_CACHE_HOME="${HOME}/.cache"
	export UV_PYTHON_INSTALL_DIR="${CI_PROJECT_DIR}/build/runtime/tool-cache/python"
	# Preserve the Runner script on stdin; setup must not consume it.
	bash "${BASH_SOURCE[0]}" </dev/null
	owned_roots=("${CI_PROJECT_DIR}")
	if [[ -n ${ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR:-} ]]; then
		cache="/cache/${CI_PROJECT_PATH_SLUG:?}/ci-tools"
		[[ ${ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR} == "${cache}" ]] || exit 2
		mkdir -p -- "${cache}"
		[[ "$(cd -- "${cache}" && pwd -P)" == "${cache}" ]] || exit 2
		owned_roots+=("${cache}")
	fi
	mkdir -p -- "${HOME}"
	for owned_root in "${owned_roots[@]}"; do
		find "${owned_root}" -xdev ! -type l -exec chown --no-dereference 65534:65534 {} +
	done
	# Replace PID 1 before Runner creates shells, proof or pytest children.
	exec setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"
export UV_PROJECT_ENVIRONMENT="${repo_root}/.venv"
host_os="$(uname -s)"

case "${host_os}" in
Linux)
	missing_packages=()
	if ! command -v git >/dev/null 2>&1; then missing_packages+=(git); fi
	if ! command -v ssh-keygen >/dev/null 2>&1; then missing_packages+=(openssh-client); fi
	if ! command -v ps >/dev/null 2>&1; then missing_packages+=(procps); fi
	if ! command -v lsof >/dev/null 2>&1; then missing_packages+=(lsof); fi
	if ! command -v setpriv >/dev/null 2>&1; then missing_packages+=(util-linux); fi
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

python_image_available() {
	"${UV_PROJECT_ENVIRONMENT}/bin/python" -B -I - <<'PY_IMAGE'
import sys
from pathlib import Path

from ethos.adapters.repo.runtime.materialization.python_environment import (
    require_python_image_source,
)

require_python_image_source(Path(sys.executable))
PY_IMAGE
}

if ! python_image_available >/dev/null 2>&1; then
	project_python="$(
		"${UV_PROJECT_ENVIRONMENT}/bin/python" -B -I -c \
			'import platform; print(platform.python_version())'
	)"
	printf 'Provisioning shared native Python image %s\n' "${project_python}"
	uv python install --no-bin "${project_python}"
	python_image_available
fi
