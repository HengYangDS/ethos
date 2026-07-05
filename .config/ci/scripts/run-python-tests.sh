#!/usr/bin/env bash
# Run the Python trust-bearing test gate with coverage.
#
# This is the owner script for the product test gate. Hosted CI and ETHOS proof
# call this script instead of duplicating pytest/coverage policy inline.
set -euo pipefail

uv run --group dev pytest \
  --cov-config=.config/checks/coverage/coverage.ini \
  --cov=ethos \
  --cov=ethos_core \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml \
  --cov-fail-under=90 \
  tests/unit tests/architecture -q
