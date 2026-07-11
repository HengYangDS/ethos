#!/usr/bin/env bash
# Capture ignored local performance evidence for compact reader commands.
#
# The first capture establishes a same-machine baseline. Later captures update
# only latest.json; accepting a new baseline is explicit so a regression cannot
# silently redefine the reference point.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --all-packages --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

accept_baseline=false
if [[ "${1:-}" == "--accept-baseline" ]]; then
  accept_baseline=true
  shift
fi
if [[ "$#" -ne 0 ]]; then
  echo "usage: $0 [--accept-baseline]" >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

ethos_performance_head="$(tools/ci/scripts/require-stable-head.sh capture)"
_ethos_verify_performance_head_stability() {
  tools/ci/scripts/require-stable-head.sh verify \
    "${ethos_performance_head}" \
    "tools/ci/scripts/run-performance-evidence.sh"
}
trap _ethos_verify_performance_head_stability EXIT

ethos_python="${ETHOS_PYTHON:-${PYTHON:-${UV_PROJECT_ENVIRONMENT}/bin/python}}"

if ! "${ethos_python}" -c 'import ethos' >/dev/null 2>&1; then
  echo "ETHOS Python environment is unavailable: ${ethos_python}" >&2
  exit 1
fi

"${ethos_python}" - \
  ".config/checks/performance/policy.toml" \
  "${ethos_performance_head}" \
  "${accept_baseline}" <<'PY'
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import platform
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

from ethos.cli import app
from ethos.surface.cli._base import load_command_groups

policy_path = Path(sys.argv[1])
head = sys.argv[2]
accept_baseline = sys.argv[3] == "true"
policy_bytes = policy_path.read_bytes()
policy = tomllib.loads(policy_bytes.decode("utf-8"))
latest_path = Path(str(policy["latest_path"]))
baseline_path = Path(str(policy["baseline_path"]))
commands = [dict(command) for command in policy["commands"]]
samples = int(policy.get("samples", 5))
warmups = int(policy.get("warmup_samples", 1))
if samples < 1 or warmups < 0:
    raise SystemExit("performance policy sample counts must be non-negative and non-zero")


def command_name(command: dict[str, object]) -> str:
    return "ethos " + " ".join(str(item) for item in command["argv"])


def run_cold(argv: list[str]) -> tuple[float, bytes]:
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "-m", "ethos.cli", *argv],
        check=False,
        capture_output=True,
    )
    elapsed = (time.perf_counter() - started) * 1000
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise SystemExit(f"performance command failed: {' '.join(argv)}: {stderr}")
    return elapsed, completed.stdout


def run_hot(argv: list[str]) -> tuple[float, bytes]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    started = time.perf_counter()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            app(argv, exit_on_error=False)
        except SystemExit as exc:
            if exc.code not in (0, None):
                raise SystemExit(
                    f"performance command failed: {' '.join(argv)}: {stderr.getvalue().strip()}"
                ) from exc
    return (time.perf_counter() - started) * 1000, stdout.getvalue().encode("utf-8")


def p95(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * 0.95)))
    return ordered[index]


measurements: list[dict[str, object]] = []
for command in commands:
    argv = [str(item) for item in command["argv"]]
    cold, cold_payload = run_cold(argv)
    json.loads(cold_payload)
    load_command_groups(argv)
    for _ in range(warmups):
        run_hot(argv)
    hot_samples: list[float] = []
    payload = cold_payload
    for _ in range(samples):
        elapsed, payload = run_hot(argv)
        hot_samples.append(elapsed)
    json.loads(payload)
    json_bytes = len(payload)
    measurements.append(
        {
            "command": command_name(command),
            "cold_milliseconds": round(cold, 2),
            "hot_median_milliseconds": round(sorted(hot_samples)[len(hot_samples) // 2], 2),
            "hot_p95_milliseconds": round(p95(hot_samples), 2),
            "sample_count": samples,
            "json_bytes": json_bytes,
            "token_estimate": (json_bytes + 3) // 4,
        }
    )

machine = {
    "system": platform.system(),
    "release": platform.release(),
    "machine": platform.machine(),
    "python": platform.python_version(),
    "executable": shutil.which(Path(sys.executable).name) or sys.executable,
}
machine["fingerprint"] = hashlib.sha256(
    json.dumps(machine, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
payload = {
    "schema_version": 2,
    "head": head,
    "policy_digest": hashlib.sha256(policy_bytes).hexdigest(),
    "machine": machine,
    "measurement_basis": "cold_subprocess_and_hot_inprocess_samples",
    "measurements": measurements,
}
latest_path.parent.mkdir(parents=True, exist_ok=True)
latest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
if accept_baseline or not baseline_path.exists():
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
PY
