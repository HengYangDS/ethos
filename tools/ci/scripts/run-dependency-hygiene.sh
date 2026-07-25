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
mkdir -p "$(dirname "${output}")"

uv run --group dev deptry src/ethos \
  --config pyproject.toml \
  --known-first-party ethos \
  --package-module-name-map cel-python=celpy,pyyaml=yaml \
  --json-output "${output}" \
  --no-ansi

python - "${output}" <<'PY'
from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

output = Path(sys.argv[1])
payload = {
    "schema_version": 1,
    "kind": "ethos_dependency_hygiene",
    "ok": True,
    "head": subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip(),
    "config": ".config/checks/deptry/policy.toml",
    "generated_at": datetime.now(UTC).isoformat(),
    "tool": "deptry",
    "evidence_class": "local_owner_gate",
    "not_claimed": ["vulnerability scan", "hosted CI passed"],
    "outputs": [output.as_posix()],
}
path = Path("build/evidence/quality/dependency/summary.json")
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
PY
