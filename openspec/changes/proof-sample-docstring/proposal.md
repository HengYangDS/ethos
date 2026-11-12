# Proposal

## Why

The full precheck of 2026-11-13 failed
`tests/unit/cli/test_proof_execution_source.py::test_public_proof_preserves_native_failure_and_skipped_dependants`
for both parameters. Its sample repository's `src/sample/__init__.py` has no docstring, so since the
`package-docstring-rule` Change the proof refuses with
`repository_paradigm_package_docstring:src/sample/__init__.py` before any gate runs, and the test
never reaches the static failure or the pass it asserts.

## What Changes

- The sample package opens with a one-line docstring. The failing variant keeps its unused import,
  so the static gate still fails, and the test keeps proving that a failed native prerequisite
  retains its evidence and that skipped work is not a pass.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Behavior is unchanged, so `skip_specs: true` applies.

## Impact

`tests/unit/cli/test_proof_execution_source.py`.
