#!/usr/bin/env bash
# Run the Python trust-bearing test gate with coverage.
#
# This is the owner script for the product test gate. Hosted CI and ETHOS proof
# call this script instead of duplicating pytest/coverage policy inline.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

coverage_dir=".config/checks/coverage"
mkdir -p "${coverage_dir}"
export COVERAGE_FILE="${coverage_dir}/.coverage"

uv run --group dev pytest \
  --cov-config="${coverage_dir}/coverage.ini" \
  --cov=ethos \
  --cov=ethos_core \
  --cov-report=term-missing \
  --cov-report="xml:${coverage_dir}/coverage.xml" \
  --cov-fail-under=95 \
  tests/unit tests/architecture -q
