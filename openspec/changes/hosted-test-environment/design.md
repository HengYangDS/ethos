# Design

## Context

See [proposal.md](proposal.md). `locked_environment` builds a child `PATH` from the selected mise,
`mise bin-paths` and the host command baseline, and nothing else from the caller's `PATH`
(`src/ethos/adapters/toolchain/mise.py`). ETHOS's native supply downloads gitleaks, scc, Syft, Vale
and CUE with an isolated mise and keeps the verified payload in its own cache (`materialize_tool`,
`NativeSupply.cache`), so mise's installs never hold them. Before `test-runner-unification`, the
test gate inherited the hosted proof's `PATH`, to which hosted verification prepends the prepared
supply; the shipped probe does not.

The host proof (`DeliveryPipeline.prove_host`) runs four pytest cases with the shared configuration,
whose `addopts` now include `--numprocesses=auto`. On Windows pytest-timeout ends a stuck worker
with `os._exit`, so the stack it prints never reaches the controller.

## Goals / Non-Goals

**Goals:**

- Hosted verification passes on both peers with unchanged assertions, and the Windows host proof
  passes on every Windows job.
- A test that makes no progress leaves its stack in the job log on every platform.

**Non-Goals:**

- Explaining why the Windows ACL cases make no progress inside an xdist worker; it is recorded as a
  residual unknown with a probe on the Windows guest.
- Installing every declared tool through mise in hosted preparation, or changing which tools a
  repository declares.
- Replacing the PowerShell behind the Windows ACL and process observations. A cross-platform product
  calls the platform API instead of a platform shell, as `docs/research/foundations/effects.md`
  selects for the ACLs; that replacement needs Windows evidence and its own Change.
- Raising the source ceiling, which follows only when consolidation cannot keep the product within
  it.

## Decisions

- **Prepared supply joins the locked tools, not the caller's `PATH`.** The probe still refuses
  ambient tools; it adds only the cache directories that ETHOS's native supply prepared for tools
  the repository itself declares, after mise's installs so a local mise install still wins.
  Rejected: installing every declared tool through mise during hosted preparation, which downloads
  each native tool twice and changes the GitLab supply image; passing the caller's `PATH`, the
  ambient dependence the probe removed.
- **The host proof runs in one process.** Its four cases are platform boundary checks that set ACLs
  and clear the process environment; workers add their start-up time and changed the execution mode
  under which the cases were verified. Rejected: grouping the ACL cases on one worker, which needs
  `--dist=loadgroup` and changes the scheduling of every run.
- **A stuck test reports its stack before its bound.** `faulthandler_timeout` writes every thread's
  stack to the process's own standard error at 540 seconds, which a worker shares with the
  controller's log. The ACL case's own PowerShell call gets a 60-second bound, so a recurrence fails
  with both streams instead of waiting for the shared bound.
- **The lane pays for its additions by consolidation.** One facade check selects each file once,
  parses it once and applies the reason function of each kind its role admits; the report keeps one
  finding list per kind under today's keys. The unproven quality report joins the native report
  readers in `quality_reports`, which both gates already import. Rejected: keeping three public
  wrappers for one question, and importing one gate's helper into the language-neutral gate.
  `release_policy_report` and `materialize_explicit_release` stay: they implement stated
  requirements whose wiring has its own review.

## Risks / Trade-offs

- [The ACL hang inside workers stays unexplained] → The unknown names the probe; the 60-second bound
  turns a recurrence into a fast failure with its streams.
- [A slow healthy test writes its stacks at 540 seconds] → No test takes more than 61 seconds today,
  and writing the stacks does not fail it.
- [A stale prepared cache could shadow nothing but a missing install] → The directories follow
  mise's installs, and the native supply verifies its payload whenever it prepares it.
- [The layout report lists the three facade kinds together] → Their keys and contents are unchanged;
  only their position in the report object moves.
