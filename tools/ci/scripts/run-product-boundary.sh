#!/usr/bin/env bash
# Run product-boundary and contributor-policy gates through the ETHOS command plane.
# This keeps active product surfaces and release metadata neutral, while
# historical evidence remains classified as historical instead of product default.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --all-packages --group dev python -m ethos.cli quality product-boundary --json
uv run --all-packages --group dev python -m ethos.cli quality contributor-policy --json
