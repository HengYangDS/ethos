#!/usr/bin/env bash
# Emit ETHOS-native release supply-chain evidence envelopes. This does not publish
# a release, upload signatures, or claim hosted CI status.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${script_dir}/with-python-runtime.sh" -- uv run --package ethos python tools/ci/release_supply_chain.py
