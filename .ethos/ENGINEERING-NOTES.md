# Lane Engineering Notes (ignored, not tracked truth)

## Test environment resolution (CRITICAL — verified 2026-07-02)

pytest in this lane uses `pyproject.toml [tool.pytest.ini_options] pythonpath`
(RELATIVE paths `packages/*/src`), resolved from the lane cwd. Therefore:

- **pytest ALWAYS tests LANE code**, not the main repo. Confirmed: test_governance_profiles.py
  (a file only the lane has) collects+passes; `ethos_repository.governance_profiles.__file__`
  resolves to the lane path under pytest.
- The venv editable-install `.pth` hardcodes ABSOLUTE main-repo paths
  (`/Users/yheng/projects/ethos/packages/*/src`). This ONLY affects bare
  `import ethos.cli` (non-pytest) and the `ethos` CLI binary — NOT pytest.
- **Consequence for verification**: `python -m pytest ...` from the lane cwd is the
  AUTHORITATIVE verifier. Do NOT verify via the `ethos` CLI binary (it runs main-repo code).
  B/C/E1 green results are trustworthy (they ran under lane pytest).

## E2 (quality-proof-ratchet) status & method

- Source: work/quality-proof-ratchet, real payload = commit 0d11715 (21 files +713/-92);
  branch is stale-base fork, use `git diff 998ef40..qpr` NOT `dev..qpr` (phantom -14167).
- DO PORT verbatim: ethos-quality/gates.py (== merge-base).
- DO recalibrate: .ethos/rules.toml [quality.code_size] thresholds — baseline real sizes
  exceed QPR's stale numbers (cli.py 2897→3000, test_cli_contracts 3131→3300, test_parity 1719→1900).
- DO 3-way merge: repository/gates.py (default_gate_ids +6 ids, keep repository-audit),
  cli.py (import shutil + 5 helpers after _sha256_file + 6 commands), docs_registry KNOWN_ETHOS_COMMANDS +6.
- DO NOT port: parity.py (baseline has superior product_head model), status.py (baseline
  made coordination_gaps advisory — porting reverts a governance decision).
- Test reconciliation REQUIRED: test_cli_contracts test_quality_help_lists_canonical_commands
  expected set needs +6 commands (it's a set, order-free).
- OPEN BUG from last attempt: inserting the 6 commands produced CommandCollisionError
  "markdown-links already registered" — the insertion double-registered or collided.
  Next attempt: after inserting, grep for duplicate `@quality_app.command(name="X")` AND
  verify `python -c "import ethos.cli"` under lane PYTHONPATH before running pytest.
