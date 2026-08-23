#!/usr/bin/env bash
# Install gitleaks from a prebuilt release binary for hosted secret scanning.
#
# gitleaks is a Go CLI with no PyPI distribution, so it cannot ride the uv
# toolchain the way the Python gates do. Downloading the prebuilt release binary
# for the runner architecture keeps the secrets gate deterministic and avoids a
# Go build in CI.
#
# Kept outside .gitlab-ci.yml so CI stays a projection over reusable setup logic.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
policy_path="${repo_root}/.config/checks/secrets/supply.toml"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

read -r version linux_x64_sha256 linux_arm64_sha256 < <(
	"${script_dir}/with-python-runtime.sh" -- uv run --no-sync python - "${policy_path}" <<'PY_POLICY'
import sys
import tomllib
from pathlib import Path

policy = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
checksums = policy["archive_sha256"]
print(policy["version"], checksums["linux_x64"], checksums["linux_arm64"])
PY_POLICY
)

if command -v gitleaks >/dev/null 2>&1; then
	# Local developers (e.g. `brew install gitleaks`) already have it; skip the
	# download when the installed version already matches the pin.
	if [ "$(gitleaks version 2>/dev/null)" = "${version}" ]; then
		gitleaks version
		exit 0
	fi
fi

if ! command -v curl >/dev/null 2>&1; then
	apt-get update
	apt-get install -y --no-install-recommends curl ca-certificates tar coreutils
elif ! command -v tar >/dev/null 2>&1 || ! command -v sha256sum >/dev/null 2>&1; then
	apt-get update
	apt-get install -y --no-install-recommends tar coreutils
fi

case "$(uname -m)" in
x86_64 | amd64)
	arch="x64"
	archive_sha256="${linux_x64_sha256}"
	;;
aarch64 | arm64)
	arch="arm64"
	archive_sha256="${linux_arm64_sha256}"
	;;
*)
	echo "Unsupported gitleaks architecture: $(uname -m)" >&2
	exit 1
	;;
esac

archive="gitleaks_${version}_linux_${arch}.tar.gz"
url="https://github.com/gitleaks/gitleaks/releases/download/v${version}/${archive}"

cache_root="${ETHOS_CI_TOOL_CACHE_DIR:-${CI_PROJECT_DIR:-$(pwd)}/build/runtime/tool-cache/ci-tools}"
cache_dir="${cache_root}/gitleaks/${version}/${arch}"
archive_path="${cache_dir}/${archive}"
persistent_cache_root="${ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR:-}"
if [ -n "${persistent_cache_root}" ]; then
	persistent_cache_dir="${persistent_cache_root}/gitleaks/${version}/linux-${arch}"
	persistent_archive_path="${persistent_cache_dir}/${archive}"
else
	persistent_cache_dir=""
	persistent_archive_path=""
fi
tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

mkdir -p "${cache_dir}"

verify_archive_checksum() {
	printf '%s  %s\n' "${archive_sha256}" "$1" | sha256sum -c -
}

if [ -n "${persistent_archive_path}" ] &&
	[ -s "${persistent_archive_path}" ] &&
	tar tzf "${persistent_archive_path}" >/dev/null 2>&1 &&
	verify_archive_checksum "${persistent_archive_path}" >/dev/null 2>&1; then
	cp "${persistent_archive_path}" "${archive_path}"
fi

if [ ! -s "${archive_path}" ] || ! tar tzf "${archive_path}" >/dev/null 2>&1 || ! verify_archive_checksum "${archive_path}" >/dev/null 2>&1; then
	rm -f "${archive_path}"
	echo "Installing gitleaks ${version} for linux-${arch} from ${url}"
	"${script_dir}/download-file.sh" "${url}" "${archive_path}"
fi

verify_archive_checksum "${archive_path}"
if [ -n "${persistent_archive_path}" ]; then
	mkdir -p "${persistent_cache_dir}"
	cp "${archive_path}" "${persistent_archive_path}.tmp"
	mv "${persistent_archive_path}.tmp" "${persistent_archive_path}"
fi

if ! tar tzf "${archive_path}" | grep -qx 'gitleaks'; then
	echo "gitleaks binary not found in ${archive_path}" >&2
	tar tzf "${archive_path}" >&2
	exit 1
fi

tar -xzf "${archive_path}" -C "${tmpdir}" gitleaks
install -m 0755 "${tmpdir}/gitleaks" /usr/local/bin/gitleaks
gitleaks version
