# Proposal

## Why

Proof b10p4 of 2026-11-13 failed in `tests/architecture/test_parallel_implementations.py`
(`test_no_behavior_is_implemented_twice`). The `text-layout-rule` Change added
`tests/unit/adapters/gates/test_source_format_canonical_text.py` with a private `_command` helper
whose body repeats `_command` in `tests/unit/adapters/gates/test_source_format.py`. The
architecture test allows one implementation of each behavior.

## What Changes

- The canonical-text test runs `lane format` through the shared `run_ethos` helper of
  `tests/support/ethos_cli_runner.py`, which asserts a zero exit and returns the bounded payload.
  Its own `_command` copy goes, and its assertions keep their meaning.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Behavior is unchanged, so `skip_specs: true` applies.

## Impact

`tests/unit/adapters/gates/test_source_format_canonical_text.py`.
