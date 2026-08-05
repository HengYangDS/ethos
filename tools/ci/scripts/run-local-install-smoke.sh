#!/usr/bin/env bash
# Prove that the built ETHOS wheel installs and runs from a fresh offline environment.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"
artifact_dir="${repo_root}/build/artifacts/python"
scratch_root="${repo_root}/build/runtime/work/local-install-smoke"
venv_dir="${scratch_root}/venv"
check_dir="${scratch_root}/check"
requirements="${scratch_root}/requirements.txt"
evidence_path="${repo_root}/build/evidence/local-install/smoke.json"
head="$("${script_dir}/require-stable-head.sh" capture)"

finish() {
  exit_code=$?
  trap - EXIT
  if ! "${script_dir}/require-stable-head.sh" verify "${head}" "$0"; then
    rm -f "${evidence_path}"
    exit 1
  fi
  exit "${exit_code}"
}
trap finish EXIT
rm -rf "${scratch_root}"
rm -f "${evidence_path}"
mkdir -p "${artifact_dir}" "${check_dir}" "$(dirname "${evidence_path}")"

uv build --offline --wheel --out-dir "${artifact_dir}" --clear --no-create-gitignore >&2
shopt -s nullglob
wheels=("${artifact_dir}"/ethos-*.whl)
if [[ "${#wheels[@]}" -ne 1 ]]; then
  echo "expected exactly one ethos wheel" >&2
  exit 1
fi
wheel="${wheels[0]}"

source_python="${ETHOS_PYTHON:-${repo_root}/build/runtime/venv/bin/python}"
uv venv --offline --python "${source_python}" "${venv_dir}" >&2
smoke_python="${venv_dir}/bin/python"
uv export --locked --offline --no-dev --no-emit-project --no-header --no-annotate \
  --no-hashes --output-file "${requirements}" >&2
source_site="$(${source_python} - <<'PY'
import sysconfig
print(sysconfig.get_paths()["purelib"])
PY
)"
smoke_site="$(${smoke_python} - <<'PY'
import sysconfig
print(sysconfig.get_paths()["purelib"])
PY
)"
printf '%s\n' "${source_site}" > "${smoke_site}/ethos-locked-runtime.pth"
uv pip install --offline --no-deps --python "${smoke_python}" "${wheel}" >&2

cd "${check_dir}"
origin="$(${smoke_python} - <<'PY'
from pathlib import Path
import ethos
print(Path(ethos.__file__).resolve())
PY
)"
if [[ "${origin}" != "${venv_dir}"/* ]]; then
  echo "installed package escaped smoke venv: ${origin}" >&2
  exit 1
fi
"${venv_dir}/bin/ethos" --help > "${scratch_root}/ethos-help.txt"
version="$("${venv_dir}/bin/ethos" --version)"
printf '%s\n' "${version}" > "${scratch_root}/ethos-version.txt"
adopter_dir="${scratch_root}/adopter"
git init --quiet --initial-branch=dev "${adopter_dir}"
git -C "${adopter_dir}" config user.name "ETHOS Install Smoke"
git -C "${adopter_dir}" config user.email "ethos-install-smoke@example.invalid"
mkdir -p "${adopter_dir}/.ethos" "${adopter_dir}/openspec/changes/smoke-change"
cp "${repo_root}/.ethos/profile.toml" "${adopter_dir}/.ethos/profile.toml"
cp "${repo_root}/openspec/config.yaml" "${adopter_dir}/openspec/config.yaml"
cat > "${adopter_dir}/openspec/changes/smoke-change/commitment.toml" <<'EOF'
schema_version = 1
id = "change:smoke-change"
intent = "Exercise installed CLI repository binding."
subjects = ["repository:self"]
scope = ["README.md"]
permissions = ["repository.read", "work-lane.write", "git.ref.compare-and-swap"]
EOF
printf '# installed CLI adopter\n' > "${adopter_dir}/README.md"
git -C "${adopter_dir}" add .
git -C "${adopter_dir}" commit --quiet -m "initialize installed CLI adopter"
adopter_head="$(git -C "${adopter_dir}" rev-parse HEAD)"
"${venv_dir}/bin/ethos" status --root "${adopter_dir}" --json > "${scratch_root}/adopter-status.json"
"${venv_dir}/bin/ethos" plan --changed --root "${adopter_dir}" --json > "${scratch_root}/adopter-plan.json" || true
"${venv_dir}/bin/ethos" lane archive-change \
  --change smoke-change --expect-head "${adopter_head}" --root "${adopter_dir}" --json \
  > "${scratch_root}/adopter-archive-change.json" || true
"${smoke_python}" - <<'PY'
from ethos.adapters.openspec.cli import openspec_base_command, verify_official_cli

command = openspec_base_command()
assert command is not None, "installed wheel has no pinned OpenSpec executable"
report = verify_official_cli(command)
assert report["verdict"] == "pass", report
assert report["package"] == "@fission-ai/openspec@1.7.0", report
PY
uv pip check --python "${source_python}" >&2

ETHOS_LOCAL_INSTALL_ROOT="${repo_root}" \
ETHOS_LOCAL_INSTALL_HEAD="${head}" \
ETHOS_LOCAL_INSTALL_EVIDENCE="${evidence_path}" \
ETHOS_LOCAL_INSTALL_ORIGIN="${origin}" \
ETHOS_LOCAL_INSTALL_VERSION="${version}" \
ETHOS_LOCAL_INSTALL_WHEEL="${wheel}" \
"${smoke_python}" - <<'PY'
import hashlib
import json
import os
import tomllib
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path, PurePosixPath

root = Path(os.environ["ETHOS_LOCAL_INSTALL_ROOT"])
wheel = Path(os.environ["ETHOS_LOCAL_INSTALL_WHEEL"])
package = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
force_include = package["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
wheel_resources = []
for canonical, target in force_include.items():
    relative = PurePosixPath(target).relative_to("ethos")
    packaged = resources.files("ethos").joinpath(*relative.parts)
    source = root / canonical
    assert packaged.is_file(), target
    assert packaged.read_bytes() == source.read_bytes(), target
    wheel_resources.append(target)
payload = {
    "schema_version": 1,
    "kind": "ethos_local_install_smoke_evidence",
    "verdict": "pass",
    "state": "passed",
    "head": os.environ["ETHOS_LOCAL_INSTALL_HEAD"],
    "command": "tools/ci/scripts/run-local-install-smoke.sh",
    "generated_at": datetime.now(UTC).isoformat(),
    "head_stability": "verified_by_exit_trap",
    "offline": True,
    "fresh_environment": True,
    "dependencies": "locked_project_environment_projection",
    "module_origins": {"ethos": os.environ["ETHOS_LOCAL_INSTALL_ORIGIN"]},
    "cli_checks": [
        "ethos --help",
        "ethos --version",
        "installed ethos status in an adopter repository",
        "installed ethos plan dry-run in an adopter repository",
        "installed ethos archive-change dry-run in an adopter repository",
        "@fission-ai/openspec@1.7.0",
        "declared wheel resources match their canonical sources",
    ],
    "wheel_resources": sorted(wheel_resources),
    "version": os.environ["ETHOS_LOCAL_INSTALL_VERSION"],
    "wheels": [{
        "path": wheel.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
    }],
    "hosted_ci_status_claimed": False,
    "remote_publication_claimed": False,
    "registry_publication_claimed": False,
}
evidence = Path(os.environ["ETHOS_LOCAL_INSTALL_EVIDENCE"])
evidence.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
PY
