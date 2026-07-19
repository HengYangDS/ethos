#!/usr/bin/env bash
# Write a closeout evidence manifest that hashes reviewed claim/chronicle/OpenSpec
# carriers. Generated logs remain generated evidence, not repository truth.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${script_dir}/with-python-runtime.sh" -- uv run --package ethos python tools/ci/closeout_manifest.py
