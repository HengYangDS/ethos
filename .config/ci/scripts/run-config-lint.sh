#!/usr/bin/env bash
# Run repository configuration quality gates.
#
# Ownership boundaries:
# - TOML format/lint policy: .config/checks/taplo/taplo.toml
# - YAML lint policy: .config/checks/yaml/yamllint.yaml
# - JSON syntax hygiene: Python stdlib parser, no formatting policy restated here.
# - Provider CI calls this script; it does not restate policy inline.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

if (($#)); then
  toml_files=()
  yaml_files=()
  json_files=()
  for target in "$@"; do
    case "${target}" in
      *.toml) toml_files+=("${target}") ;;
      *.yml|*.yaml) yaml_files+=("${target}") ;;
      *.json) json_files+=("${target}") ;;
      *) echo "unsupported config lint target: ${target}" >&2; exit 2 ;;
    esac
  done
else
  toml_files=()
  yaml_files=()
  json_files=()
  while IFS= read -r target; do
    toml_files+=("${target}")
  done < <(git ls-files '*.toml')
  while IFS= read -r target; do
    yaml_files+=("${target}")
  done < <(git ls-files '*.yml' '*.yaml')
  while IFS= read -r target; do
    json_files+=("${target}")
  done < <(git ls-files '*.json')
fi

filter_existing_files() {
  local target
  for target in "$@"; do
    [[ -f "${target}" ]] && printf '%s\n' "${target}"
  done
}

toml_existing=()
if ((${#toml_files[@]})); then
  while IFS= read -r target; do
    toml_existing+=("${target}")
  done < <(filter_existing_files "${toml_files[@]}")
fi
toml_files=()
if ((${#toml_existing[@]})); then
  toml_files=("${toml_existing[@]}")
fi

yaml_existing=()
if ((${#yaml_files[@]})); then
  while IFS= read -r target; do
    yaml_existing+=("${target}")
  done < <(filter_existing_files "${yaml_files[@]}")
fi
yaml_files=()
if ((${#yaml_existing[@]})); then
  yaml_files=("${yaml_existing[@]}")
fi

json_existing=()
if ((${#json_files[@]})); then
  while IFS= read -r target; do
    json_existing+=("${target}")
  done < <(filter_existing_files "${json_files[@]}")
fi
json_files=()
if ((${#json_existing[@]})); then
  json_files=("${json_existing[@]}")
fi

python - "${toml_files[@]}" <<'PY'
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

failed = False
for raw in sys.argv[1:]:
    path = Path(raw)
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        print(f"{path}: missing final newline", file=sys.stderr)
        failed = True
    if data.endswith(b"\n\n"):
        print(f"{path}: more than one trailing newline", file=sys.stderr)
        failed = True
    for index, line in enumerate(data.splitlines(), start=1):
        if line.rstrip(b" \t") != line:
            print(f"{path}:{index}: trailing whitespace", file=sys.stderr)
            failed = True
    try:
        tomllib.loads(data.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - style gate reports parser detail.
        print(f"{path}: TOML parse failed: {exc}", file=sys.stderr)
        failed = True
raise SystemExit(1 if failed else 0)
PY

python - "${json_files[@]}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

failed = False
for raw in sys.argv[1:]:
    path = Path(raw)
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        print(f"{path}: missing final newline", file=sys.stderr)
        failed = True
    try:
        json.loads(data.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - style gate reports parser detail.
        print(f"{path}: JSON parse failed: {exc}", file=sys.stderr)
        failed = True
raise SystemExit(1 if failed else 0)
PY

if ((${#toml_files[@]})); then
  # taplo publishes no linux-aarch64 wheel, so `uv run --with taplo` builds a broken
  # Rust sdist on the ARM runner. install-taplo.sh provides a prebuilt binary (or the
  # dev's on-PATH taplo) so format/lint run the same everywhere.
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  "${script_dir}/install-taplo.sh"
  taplo format --check \
    --config .config/checks/taplo/taplo.toml \
    "${toml_files[@]}"
  taplo lint \
    --config .config/checks/taplo/taplo.toml \
    --no-schema \
    "${toml_files[@]}"
fi

if ((${#yaml_files[@]})); then
  uv run --no-project --with yamllint yamllint --strict \
    --config-file .config/checks/yaml/yamllint.yaml \
    "${yaml_files[@]}"
fi
