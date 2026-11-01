# Proposal

## Why

After `test-runner-unification` landed at `ab1ac7e26`, the hosted verification of that head failed
on both peers, and the Windows host proof failed on every Windows job.

- The shipped Python probe runs pytest in mise's locked environment, whose `PATH` lists only the
  tools mise itself installed: `mise bin-paths` omits a declared tool that it has not installed,
  with no warning. Hosted verification prepares gitleaks, scc, syft and Vale through ETHOS's native
  supply instead (`tools/ci/toolchain/native.py`), so the staged-secret hook cases found no gitleaks
  and failed with `staged_secret_gitleaks_missing` (GitHub runs 41287150978 and 41287323997, GitLab
  pipeline 13555). The requirement that hosted verification owns its native test prerequisites no
  longer held.
- The shared pytest configuration now starts xdist workers for every run, so the host proof's four
  cases ran in four workers. Both Windows ACL cases then made no progress until the 600-second bound
  ended their workers, and no stack reached the log. The same four cases passed in one process in 6
  seconds at `1910e04df`.
- With this Change and the lane's other Changes, the Python product measures 70,005 effective lines,
  above its 70,000 ceiling. A scan for product functions with structurally identical bodies finds
  three module-layout facade checks that differ only in data, which parse every ordinary module
  twice, and one unproven quality report that two quality gates each define.

## What Changes

- The locked environment takes the locked tools that ETHOS's native supply has prepared for the
  repository, after mise's own installs and before the host baseline; the probe passes them.
- The host proof runs its four platform cases in one process.
- The ACL case bounds its own PowerShell call at 60 seconds.
- pytest writes every thread's stack after 540 seconds, before the 600-second bound ends a worker.
- One facade check parses each selected file once and reports the three facade kinds, and the
  quality report owner builds the unproven report that both quality gates return.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: hosted verification's prepared test prerequisites reach the probe's tests, and a test
  that makes no progress reports its stack on every platform.
- `proof-hosts`: the host proof runs its platform cases in one process.

## Impact

`src/ethos/adapters/toolchain/mise.py`,
`src/ethos/adapters/repo/runtime/materialization/native_supply.py`,
`src/ethos/adapters/gates/python_quality.py`, `tools/ci/delivery/pipeline.py`,
`.config/checks/pytest/pytest.toml`, `src/ethos/repository/policy/layout/facades.py`,
`src/ethos/repository/policy/quality_reports.py`, `src/ethos/adapters/gates/code_quality.py`, their
tests and the `quality` and `proof-hosts` specifications. A repository whose native supply ETHOS has
not prepared sees no change; module-layout findings and quality reports are unchanged.
