#!/usr/bin/env bash
# Prove that built ETHOS wheels install and run from a fresh offline environment.
# This is local, HEAD-bound evidence; it does not publish or claim hosted CI.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- uv run --all-packages --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; cd "${repo_root}"; artifact_dir="${repo_root}/build/artifacts/python"; scratch_root="${repo_root}/build/runtime/work/local-install-smoke"; venv_dir="${scratch_root}/venv"; check_dir="${scratch_root}/check"; evidence_path="${repo_root}/build/evidence/local-install/smoke.json"

local_install_head="$("${script_dir}/require-stable-head.sh" capture)"
_ethos_finalize_local_install_smoke() {
  exit_code=$?; trap - EXIT
  if ! "${script_dir}/require-stable-head.sh" verify \
    "${local_install_head}" "tools/ci/scripts/run-local-install-smoke.sh"; then rm -f "${evidence_path}"; exit 1; fi
  exit "${exit_code}"
}
trap _ethos_finalize_local_install_smoke EXIT; rm -rf "${scratch_root}"; rm -f "${evidence_path}"; mkdir -p "${artifact_dir}" "${check_dir}" "$(dirname "${evidence_path}")"

uv build --offline --all-packages --wheel --out-dir build/artifacts/python --clear --no-create-gitignore >&2

shopt -s nullglob; ethos_wheels=("${artifact_dir}"/ethos-*.whl); core_wheels=("${artifact_dir}"/ethos_core-*.whl)
if [[ "${#ethos_wheels[@]}" -ne 1 || "${#core_wheels[@]}" -ne 1 ]]; then echo "expected exactly one ethos wheel and one ethos-core wheel" >&2; exit 1; fi

source_python="${ETHOS_PYTHON:-${repo_root}/build/runtime/venv/bin/python}"; env -u VIRTUAL_ENV UV_PROJECT_ENVIRONMENT="${venv_dir}" uv sync --locked --offline --all-packages --no-dev --no-install-workspace --python "${source_python}" >&2
smoke_python="${venv_dir}/bin/python"; smoke_ethos="${venv_dir}/bin/ethos"; uv pip install --offline --no-deps --python "${smoke_python}" "${core_wheels[0]}" "${ethos_wheels[0]}" >&2; uv pip check --python "${smoke_python}" >&2

cd "${check_dir}"
origins_json="$(VIRTUAL_ENV="${venv_dir}" "${smoke_python}" - <<'PY'
import json, os; from pathlib import Path; import ethos, ethos_core
venv = Path(os.environ["VIRTUAL_ENV"]).resolve(); origins = {"ethos": Path(ethos.__file__).resolve(), "ethos_core": Path(ethos_core.__file__).resolve()}
if not all(path.is_relative_to(venv) for path in origins.values()): raise SystemExit(f"installed package escaped smoke venv: {origins}")
print(json.dumps({name: path.as_posix() for name, path in origins.items()}, sort_keys=True))
PY
)"
"${smoke_ethos}" --help > "${scratch_root}/ethos-help.txt"; version="$("${smoke_ethos}" --version)"; printf '%s\n' "${version}" > "${scratch_root}/ethos-version.txt"

env ETHOS_LOCAL_INSTALL_ROOT="${repo_root}" ETHOS_LOCAL_INSTALL_HEAD="${local_install_head}" ETHOS_LOCAL_INSTALL_EVIDENCE="${evidence_path}" ETHOS_LOCAL_INSTALL_ORIGINS="${origins_json}" ETHOS_LOCAL_INSTALL_VERSION="${version}" ETHOS_LOCAL_INSTALL_ETHOS_WHEEL="${ethos_wheels[0]}" ETHOS_LOCAL_INSTALL_CORE_WHEEL="${core_wheels[0]}" "${smoke_python}" - <<'PY'
import hashlib, json, os; from datetime import UTC, datetime; from pathlib import Path
root = Path(os.environ["ETHOS_LOCAL_INSTALL_ROOT"]); evidence = Path(os.environ["ETHOS_LOCAL_INSTALL_EVIDENCE"])
wheels = [{"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in map(Path, (os.environ["ETHOS_LOCAL_INSTALL_CORE_WHEEL"], os.environ["ETHOS_LOCAL_INSTALL_ETHOS_WHEEL"]))]
payload = {"schema_version": 1, "kind": "ethos_local_install_smoke_evidence", "ok": True, "state": "passed", "head": os.environ["ETHOS_LOCAL_INSTALL_HEAD"], "command": "tools/ci/scripts/run-local-install-smoke.sh", "generated_at": datetime.now(UTC).isoformat(), "head_stability": "verified_by_exit_trap", "offline": True, "fresh_environment": True, "module_origins": json.loads(os.environ["ETHOS_LOCAL_INSTALL_ORIGINS"]), "cli_checks": ["ethos --help", "ethos --version"], "version": os.environ["ETHOS_LOCAL_INSTALL_VERSION"], "wheels": wheels, "hosted_ci_status_claimed": False, "remote_publication_claimed": False, "registry_publication_claimed": False}
evidence.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps(payload, indent=2, sort_keys=True))
PY
