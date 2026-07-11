#!/usr/bin/env bash
# Run dependency hygiene with deptry per Python distribution.
#
# Boundary: this is package metadata hygiene. It does not audit vulnerabilities
# and it does not treat the workspace root as a Python runtime package.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --all-packages --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

mkdir -p build/evidence/quality/dependency

uv run --group dev deptry packages/ethos/src/ethos \
  --config packages/ethos/pyproject.toml \
  --known-first-party ethos \
  --json-output build/evidence/quality/dependency/deptry-ethos.json \
  --no-ansi

uv run --group dev deptry packages/ethos-core/src/ethos_core \
  --config packages/ethos-core/pyproject.toml \
  --known-first-party ethos_core \
  --per-rule-ignores DEP003=jsonschema \
  --json-output build/evidence/quality/dependency/deptry-ethos-core.json \
  --no-ansi

python - <<'PY'
from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

root = Path.cwd()
head = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
).stdout.strip()
outputs = [
    "build/evidence/quality/dependency/deptry-ethos.json",
    "build/evidence/quality/dependency/deptry-ethos-core.json",
]
payload = {
    "schema_version": 1,
    "kind": "ethos_dependency_hygiene",
    "ok": True,
    "head": head,
    "config": ".config/checks/deptry/policy.toml",
    "generated_at": datetime.now(UTC).isoformat(),
    "tool": "deptry",
    "evidence_class": "local_owner_gate",
    "not_claimed": ["vulnerability scan", "hosted CI passed"],
    "outputs": outputs,
}
path = root / "build/evidence/quality/dependency/summary.json"
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
PY
