#!/usr/bin/env bash
# Validate dependency declarations for the sole ETHOS Python distribution.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

output="build/evidence/quality/dependency/deptry-ethos.json"
summary="build/evidence/quality/dependency/summary.json"
mkdir -p "$(dirname "${output}")"
rm -f "${output}" "${summary}"

set +e
uv run --group dev deptry src/ethos \
  --config pyproject.toml \
  --known-first-party ethos \
  --package-module-name-map cel-expr-python=cel_expr_python,pyyaml=yaml \
  --json-output "${output}" \
  --no-ansi
deptry_exit=$?
set -e

python3 - "${output}" "${summary}" "${deptry_exit}" <<'PY'
from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

output, path = map(Path, sys.argv[1:3])
deptry_exit = int(sys.argv[3])
try:
    findings = json.loads(output.read_text(encoding="utf-8"))
    if not isinstance(findings, list):
        raise TypeError
except (OSError, TypeError, json.JSONDecodeError):
    verdict, state = "unknown", "unobservable"
    required_gaps = [
        "dependency_hygiene_output_unparseable"
        if output.is_file()
        else "dependency_hygiene_execution_failed"
    ]
else:
    if findings:
        verdict, state = "block", "findings_reported"
        required_gaps = ["dependency_hygiene_findings_reported"]
    elif deptry_exit:
        verdict, state = "unknown", "unobservable"
        required_gaps = ["dependency_hygiene_execution_failed"]
    else:
        verdict, state, required_gaps = "pass", "passed", []

payload = {
    "schema_version": 1,
    "kind": "ethos_dependency_hygiene",
    "verdict": verdict,
    "state": state,
    "head": subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip(),
    "config": ".config/checks/deptry/policy.toml",
    "generated_at": datetime.now(UTC).isoformat(),
    "tool": "deptry",
    "evidence_class": "local_owner_gate",
    "required_gaps": required_gaps,
    "not_claimed": ["vulnerability scan", "hosted CI passed"],
    "outputs": [output.as_posix()],
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
raise SystemExit(0 if verdict == "pass" else 1)
PY
