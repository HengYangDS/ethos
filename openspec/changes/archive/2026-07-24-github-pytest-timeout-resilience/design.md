## Context

The default pytest policy is intentionally portable: `timeout = 120` and
`timeout_method = thread`. In `pytest-timeout`, the thread handler ends a timed
out process with `os._exit(1)`. Under xdist this appears as a lost worker and
can leave the controller waiting without a useful test-level timeout verdict.

On July 24, 2026, GitHub runs for accepted commit `22e8ad695` reproduced this
failure on both `dev` and `main`. A bounded diagnostic on the same checkout and
runner completed all 2,954 tests with four workers in 286.25 seconds when each
test used a 300-second signal timeout. The slowest individual test remained
well below the new bound. GitLab already uses one worker and passed the same
accepted commit, so its projection does not need this provider-specific policy.

## Goals / Non-Goals

**Goals:**

- Preserve a finite timeout while converting a macOS timeout into an observable
  pytest failure rather than an abrupt worker exit.
- Keep timeout policy in the reusable owner script and make provider YAML only
  select validated inputs.
- Retain four GitHub workers and the global portable defaults.
- Require fresh hosted evidence before claiming the repair complete.

**Non-Goals:**

- Masking genuine hangs or test failures.
- Applying signal mode globally or to unsupported platforms.
- Adding automatic retries, runner restarts, or hardware changes.
- Advancing accepted or remote refs that contain foreign candidate work without
  the required authority.

## Decisions

1. **Use paired owner-script inputs.** `ETHOS_TEST_TIMEOUT_SECONDS` and
   `ETHOS_TEST_TIMEOUT_METHOD` are optional together and invalid separately.
   Seconds must be a positive integer and the method must be `signal` or
   `thread`. This keeps provider YAML declarative and prevents arbitrary
   `PYTEST_ADDOPTS` from becoming the policy surface.
2. **Keep the global default unchanged.** When neither input is present, pytest
   continues to read 120 seconds and thread mode from its canonical config.
3. **Scope signal mode to GitHub macOS repository proof.** The generated GitHub
   `verify` job sets `300` and `signal`; local, adopter, and GitLab paths retain
   their existing behavior. Signal mode is suitable because this job is
   explicitly macOS and pytest executes tests in each worker's main thread.
4. **Retain four workers.** The failure mechanism is abrupt timeout-process
   termination, not evidence that parallelism itself violates isolation. Four
   workers keep the hosted proof within its established operating envelope.
5. **Do not use blind reruns as acceptance.** Focused contracts, exact-HEAD
   proof, and new GitHub/GitLab hosted observations remain separate required
   evidence.

## Risks / Trade-offs

- **A real hang takes longer to fail** -> retain a finite five-minute per-test
  ceiling and surface the exact timed-out test.
- **Signal mode is not portable to every platform** -> project it only into the
  explicitly macOS GitHub job.
- **An intermittent shared-state defect could remain** -> require full local
  proof plus fresh provider runs; do not infer correctness from one rerun.
- **Candidate contains unrelated owned work** -> keep this change in its own
  leased Work Lane and evaluate accepted-root authority separately after land.

## Migration Plan

1. Add failing architecture contracts for validation and provider projection.
2. Implement owner-script parsing and project the template into the generated
   workflow.
3. Run focused gates and exact-HEAD proof, then land only this Work Lane.
4. Publish only refs for which authority and ancestry are current, and require
   green GitHub and GitLab observations before final closeout.

Rollback removes the three GitHub environment values and the optional owner-
script arguments, restoring the unchanged global pytest defaults.

## Open Questions

None. Hosted results remain evidence, not assumed outcomes.
