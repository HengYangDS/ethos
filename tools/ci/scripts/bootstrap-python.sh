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
	export UV_PYTHON_INSTALL_DIR="${UV_PYTHON_INSTALL_DIR:-${CI_PROJECT_DIR}/build/runtime/tool-cache/python}"
	mkdir -p -- "${HOME}"
	find "${CI_PROJECT_DIR}" -xdev ! -type l -exec chown --no-dereference 65534:65534 {} +
	# Supply is immutable and writable by the target UID; never prime its cache as root.
	# The bootstrap child does not consume the Runner script on stdin.
	# The child, not the root shell, must expand CI_PROJECT_DIR and runner arguments.
	# shellcheck disable=SC2016
	exec setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs \
		/bin/bash -c 'bash "$CI_PROJECT_DIR/tools/ci/scripts/bootstrap-python.sh" </dev/null && exec "$@"' \
		ethos-ci-entrypoint "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"
export UV_PROJECT_ENVIRONMENT="${repo_root}/.venv"
host_os="$(uname -s)"

if [[ -n ${ETHOS_CI_SUPPLY_MANIFEST:-} ]]; then
	if [[ ! -f ${ETHOS_CI_SUPPLY_MANIFEST} ]] ||
		! sha256sum --check --status "${ETHOS_CI_SUPPLY_MANIFEST}"; then
		echo 'ci_supply_input_mismatch' >&2
		exit 2
	fi
fi

case "${host_os}" in
Linux)
	missing_packages=()
	if ! command -v git >/dev/null 2>&1; then missing_packages+=(git); fi
	if ! command -v ssh-keygen >/dev/null 2>&1; then missing_packages+=(openssh-client); fi
	if ! command -v ps >/dev/null 2>&1; then missing_packages+=(procps); fi
	if ! command -v lsof >/dev/null 2>&1; then missing_packages+=(lsof); fi
	if ! command -v setpriv >/dev/null 2>&1; then missing_packages+=(util-linux); fi
	if ! command -v ldconfig >/dev/null 2>&1 ||
		! ldconfig -p 2>/dev/null | grep 'libatomic\.so\.1' >/dev/null; then
		missing_packages+=(libatomic1)
	fi
	if ((${#missing_packages[@]})); then
		if [[ -n ${ETHOS_CI_SUPPLY_MANIFEST:-} ]]; then
			printf 'ci_supply_prerequisite_missing: %s\n' "${missing_packages[*]}" >&2
			exit 2
		fi
		if ! command -v apt-get >/dev/null 2>&1; then
			printf 'missing Linux prerequisites and apt-get is unavailable: %s\n' "${missing_packages[*]}" >&2
			exit 1
		fi
		apt-get update -o APT::Update::Error-Mode=any
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

# The runner/operator supplies this protected public anchor outside the checkout.
# No candidate key discovery, signer generation or user identity mutation occurs.
if [[ -n ${ETHOS_COMMIT_TRUST_ANCHOR:-} || -n ${ETHOS_COMMIT_ALLOWED_SIGNERS:-} ]]; then
	"${UV_PROJECT_ENVIRONMENT}/bin/python" -B - "${repo_root}" <<'PY_TRUST'
import os
import sys
from pathlib import Path
from tools.ci.toolchain.environment import bind_commit_trust, bind_commit_trust_material

path, material = os.getenv("ETHOS_COMMIT_TRUST_ANCHOR"), os.getenv("ETHOS_COMMIT_ALLOWED_SIGNERS")
if path and material:
    raise ValueError("ci_commit_trust_inputs_ambiguous")
if material:
    bind_commit_trust_material(Path(sys.argv[1]), material)
elif path:
    bind_commit_trust(Path(sys.argv[1]), Path(path))
PY_TRUST
fi

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
