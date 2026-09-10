#!/usr/bin/env bash
# Materialize verified budget-tool supply in the repository cache; print its bin directory.
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != 1 ]]; then
	exec "${script_dir}/with-python-runtime.sh" -- uv run --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
policy_path="${repo_root}/.config/checks/format/selection.toml"
os="$(uname -s)"
case "${os}" in
Linux | Darwin) ;;
*)
	echo "scc_unsupported_platform:${os}" >&2
	exit 2
	;;
esac
case "$(uname -m)" in
aarch64 | arm64) arch=arm64 ;;
x86_64 | amd64) arch=x86_64 ;;
*)
	echo "scc_unsupported_architecture:$(uname -m)" >&2
	exit 2
	;;
esac
supply="$(
	python - "${policy_path}" "${os}_${arch}" <<'PY'
import re
import sys
import tomllib
from pathlib import Path

policy = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["budget_tool_supply"]
version, digest = policy["version"], policy["archive_sha256"][sys.argv[2]]
if not re.fullmatch(r"\d+\.\d+\.\d+", version) or not re.fullmatch(r"[0-9a-f]{64}", digest):
    raise SystemExit("scc_supply_policy_invalid")
print(version, digest)
PY
)"
read -r version digest <<<"${supply}"
cache="${ETHOS_CI_TOOL_CACHE_DIR:-${repo_root}/build/runtime/tool-cache/ci-tools}/scc/${version}/${os}_${arch}"
archive="${cache}/scc_${os}_${arch}.tar.gz"
mkdir -p "${cache}"
if [[ ! -s "${archive}" ]]; then
	"${script_dir}/download-file.sh" \
		"https://github.com/boyter/scc/releases/download/v${version}/scc_${os}_${arch}.tar.gz" \
		"${archive}" >&2
fi
temporary="$(mktemp -d "${cache}/.prepare-XXXXXX")"
trap 'rm -rf "${temporary}"' EXIT
python - "${archive}" "${digest}" "${version}" "${temporary}/scc" <<'PY'
import hashlib
import subprocess
import sys
import tarfile
from pathlib import Path

archive, digest, version, target = sys.argv[1:]
path = Path(target)
with Path(archive).open("rb") as stream:
    if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
        raise SystemExit("scc_archive_checksum_mismatch")
    stream.seek(0)
    with tarfile.open(fileobj=stream, mode="r:gz") as package:
        members = [member for member in package.getmembers() if member.name == "scc"]
        if len(members) != 1 or not members[0].isfile():
            raise SystemExit("scc_archive_executable_invalid")
        source = package.extractfile(members[0])
        if source is None:
            raise SystemExit("scc_archive_executable_missing")
        with source:
            path.write_bytes(source.read())
path.chmod(0o755)
result = subprocess.run([str(path), "--version"], capture_output=True, text=True, timeout=10)
if result.returncode or result.stderr or result.stdout.strip() != f"scc version {version}":
    raise SystemExit("scc_executable_version_mismatch")
PY
mv -f "${temporary}/scc" "${cache}/scc"
printf '%s\n' "${cache}"
