# Proposal

## Why

On 2026-11-10 a scratch test run put pytest's base temporary directory inside the ETHOS checkout.
`test_ref_intent` treats `tmp_path` as a non-repository root, but product code discovers a
repository by walking up from a path. So `ref_intent_dir(tmp_path)` found the real repository, and
the test wrote four fake `candidate.accept` intents into its `.git/ethos/ref-intent/`. They were
moved out before any landing read them. Any test run whose temporary root sits inside a work tree
has the same exposure, and nothing refuses it.

## What Changes

- The test session refuses to start when pytest's base temporary directory is inside a Git work
  tree or Git directory. It stops with a message that names the directory and asks for
  `--basetemp` outside any repository.
- The check reads Git with every `GIT_` variable removed from its environment, so an ambient
  `GIT_DIR` cannot hide the enclosing repository.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Test support changes; no requirement changes.

## Impact

`tests/support/git_isolation.py`, `tests/conftest.py` and one test in
`tests/architecture/test_test_fixture_boundaries.py`.
