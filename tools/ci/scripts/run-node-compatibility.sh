#!/usr/bin/env bash
# Verify the ETHOS npm launcher against one exact release declared by the Node
# runtime compatibility policy. Hosted providers select NODE_VERSION; a direct
# invocation uses the current hosted default without promoting the candidate.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

policy_path="${repo_root}/.config/checks/node/runtime.toml"
if [[ ! -f "${policy_path}" ]]; then
  echo "Node runtime compatibility policy missing: ${policy_path}" >&2
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  python_command="python3"
elif command -v python >/dev/null 2>&1; then
  python_command="python"
else
  echo "Python 3 is required to read ${policy_path}" >&2
  exit 1
fi

requested_version="${NODE_VERSION:-}"
resolved_version="$(
  "${python_command}" - "${policy_path}" "${requested_version}" <<'PY_POLICY'
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

policy_path = Path(sys.argv[1])
requested = sys.argv[2]
policy = tomllib.loads(policy_path.read_text(encoding="utf-8"))
if policy.get("schema") != "ethos-node-runtime-compatibility-v1":
    raise SystemExit(f"unsupported Node runtime policy schema: {policy.get('schema')!r}")

default = policy.get("default_version")
compatibility = policy.get("compatibility_versions")
if not isinstance(default, str) or not isinstance(compatibility, list):
    raise SystemExit("Node runtime policy must declare default_version and compatibility_versions")
if not all(isinstance(version, str) for version in compatibility):
    raise SystemExit("Node runtime compatibility_versions must contain only strings")

selected = requested or default
if selected not in compatibility:
    supported = ", ".join(compatibility)
    raise SystemExit(f"Node {selected} is outside the declared compatibility set: {supported}")
print(selected)
PY_POLICY
)"

if ! command -v node >/dev/null 2>&1; then
  echo "Node ${resolved_version} is required but node is not on PATH" >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required for Node ${resolved_version} compatibility proof" >&2
  exit 1
fi

actual_version="$(node --version)"
actual_version="${actual_version#v}"
if [[ "${actual_version}" != "${resolved_version}" ]]; then
  echo "Node runtime mismatch: requested ${resolved_version}, active ${actual_version}" >&2
  exit 1
fi

node --version
npm --version
export npm_config_engine_strict=true
npm ci --ignore-scripts
npm run ethos -- --version
npm run test:npm
