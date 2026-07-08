#!/usr/bin/env bash
# Emit ETHOS-native release supply-chain evidence envelopes. This does not publish
# a release, upload signatures, or claim hosted CI status.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --package ethos python tools/ci/release_supply_chain.py
