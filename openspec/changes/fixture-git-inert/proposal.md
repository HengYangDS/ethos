# Proposal

## Why

The full proof of `gate-efficacy-markers` failed on 2026-11-10 on one test,
`test_gate_policy_binds_committed_sources_and_reports_missing_source[tools/audit script.sh-default]`
in `tests/unit/repository/policy/test_gate_policy.py`. Its fixture repository held no loose object:
all 34 objects sat in one pack, so the blob the test damages was not where the test looks for it.
The same test failed the same way in a proof on 2026-11-07.

Every fixture `git commit` starts a detached `git maintenance run --auto` under Git 2.56.0: a
trace of 48 runs of that test recorded 384 such starts. The suite's Git overlay sets
`core.fsmonitor` and `init.templateDir`, not `maintenance.auto`. No product or fixture code packs
objects. A test repository can therefore be repacked in the background while its test runs.

## What Changes

- Every test repository runs with `maintenance.auto=false`: commits start no background
  maintenance, and objects stay as the test wrote them.
- One support constant owns the Git isolation settings. The suite overlay and the CLI runner
  read it; the runner no longer keeps its own list.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

`tests/support/git_isolation.py` (new), `tests/conftest.py`, `tests/support/ethos_cli_runner.py`
and `tests/architecture/test_pytest_configuration.py`. Product code is unchanged.
