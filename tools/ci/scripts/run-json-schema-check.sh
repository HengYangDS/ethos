#!/usr/bin/env bash
# Validate repository JSON Schema documents. This is schema hygiene only; command
# payload validation remains owned by ETHOS command JSON tests and runtime checks.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

exec "${script_dir}/with-python-runtime.sh" -- uv run --group dev check-jsonschema --check-metaschema system/schemas/**/*.json -o json
