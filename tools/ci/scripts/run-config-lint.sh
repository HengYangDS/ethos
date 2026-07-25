#!/usr/bin/env bash
# Run repository configuration quality gates.
#
# Ownership boundaries:
# - TOML format/lint policy: .config/checks/taplo/taplo.toml
# - YAML lint policy: .config/checks/yaml/yamllint.yaml
# - JSON format policy: .config/checks/json/format.toml, executed by Python stdlib json.
# - Hook config shape: .pre-commit-config.yaml, validated by locked pre-commit.
# - Provider CI calls this script; it does not restate policy inline.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
ethos_python="${ETHOS_PYTHON:-${PYTHON:-python3}}"
toml_files=() yaml_files=() json_files=()

if [[ -f .pre-commit-config.yaml ]]; then
  pre-commit validate-config .pre-commit-config.yaml
fi

if (($#)); then
  for target in "$@"; do
    case "${target}" in
      *.toml) toml_files+=("${target}") ;;
      *.yml|*.yaml) yaml_files+=("${target}") ;;
      *.json) json_files+=("${target}") ;;
      *) echo "unsupported config lint target: ${target}" >&2; exit 2 ;;
    esac
  done
else
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
  existing_files=()
  for target in "$@"; do [[ -f "${target}" ]] && existing_files+=("${target}"); done
}

if ((${#toml_files[@]})); then filter_existing_files "${toml_files[@]}"; toml_files=("${existing_files[@]}"); fi
if ((${#yaml_files[@]})); then filter_existing_files "${yaml_files[@]}"; yaml_files=("${existing_files[@]}"); fi
if ((${#json_files[@]})); then filter_existing_files "${json_files[@]}"; json_files=("${existing_files[@]}"); fi

if ((${#toml_files[@]})); then
  "${ethos_python}" - "${toml_files[@]}" <<'PY'
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
fi

if ((${#toml_files[@]})); then
  # taplo publishes no linux-aarch64 wheel, so `uv run --with taplo` builds a broken
  # Rust sdist on the ARM runner. install-taplo.sh provides a prebuilt binary (or the
  # dev's on-PATH taplo) so format/lint run the same everywhere.
  "${script_dir}/install-taplo.sh"
  RUST_LOG=warn taplo format --check \
    --config .config/checks/taplo/taplo.toml \
    "${toml_files[@]}"
  RUST_LOG=warn taplo lint \
    --config .config/checks/taplo/taplo.toml \
    --no-schema \
    "${toml_files[@]}"
fi

if ((${#json_files[@]})); then
  "${ethos_python}" - .config/checks/json/format.toml "${json_files[@]}" <<'PY'
from __future__ import annotations

import fnmatch
import json
import sys
import tomllib
from pathlib import Path

policy = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
rules = policy.get("rule", [])
failed = False
for raw in sys.argv[2:]:
    path = Path(raw)
    relative = path.as_posix()
    mode = next(
        (
            str(rule["mode"])
            for rule in reversed(rules)
            if any(fnmatch.fnmatchcase(relative, glob) for glob in rule["globs"])
        ),
        str(policy["default_mode"]),
    )
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"{relative}: JSON parse failed: {exc}", file=sys.stderr)
        failed = True
        continue
    indent = None if mode == "compact" else int(policy["indent"])
    kwargs = {"ensure_ascii": False, "indent": indent}
    if indent is None:
        kwargs["separators"] = (",", ":")
    rendered = (json.dumps(parsed, **kwargs) + "\n").encode()
    if path.read_bytes() != rendered:
        print(f"{relative}: JSON format drift ({mode})", file=sys.stderr)
        failed = True
raise SystemExit(1 if failed else 0)
PY
fi

if ((${#yaml_files[@]})); then
  uv run --no-project --with yamllint yamllint --strict \
    --config-file .config/checks/yaml/yamllint.yaml \
    "${yaml_files[@]}"
fi
