## Context

GitHub's `verify` job currently has two independent-looking steps that actually
share one test authority:

1. `tools/ci/scripts/run-python-tests.sh` directly executes all unit and
   architecture tests with coverage.
2. `tools/ci/scripts/run-head-bound-proof.sh` runs audit and report, then invokes
   `ethos prove --execute --expect-head`. The default proof graph includes the
   `unit-architecture` gate, which calls the same test owner script again.

On main run `30163837735`, step 1 passed at exact HEAD `80272b76c`, while step 2
repeated all 3,557 tests and failed on three unrelated 300-second timeouts. The
same commit also passed local exact-HEAD proof and GitHub dev CI. This is highly
consistent with shared-host pressure, but the failed main observation remains a
failure.

The user approved converging the workflow quickly without blind retry or GitLab
activity.

## Goals / Non-Goals

**Goals:**

- Execute one, and only one, full Python test graph in the GitHub repository-proof
  job.
- Keep the trust-bearing execution HEAD-bound through `ethos prove --execute`.
- Preserve two workers, the 300-second signal timeout, coverage, JUnit, digest,
  and always-uploaded proof/readiness artifacts.
- Require a fresh exact-SHA hosted result before claiming main CI green.

**Non-Goals:**

- Changing proof semantics or adding proof-receipt reuse.
- Serializing all proof activity on the workstation in this patch.
- Weakening timeouts, coverage, or any gate.
- Changing or observing GitLab.

## Approaches Considered

### A. Remove the standalone test step — selected

Keep `run-head-bound-proof.sh` as the sole repository-proof entrypoint. Its
`ethos prove --execute` call already owns the complete gate graph and produces the
HEAD-bound receipt. This is the smallest change, removes the duplicate work, and
preserves the existing evidence model.

### B. Reuse a prior standalone test receipt inside proof — rejected for now

This could retain a separate GitHub test step, but it would require a new schema,
artifact binding, cache invalidation rules, HEAD/environment/config digests, and
proof admission semantics. That is a larger trust-model change than the observed
problem requires.

### C. Add a host-global proof lock — deferred successor

A physical-host lock could prevent independent lanes from running full proofs
concurrently, but it would introduce cross-repository scheduling authority and
could block unrelated legitimate work. It should be considered only if a single
full proof still fails after duplicate execution is removed.

## Decisions

1. **One authoritative entrypoint.** GitHub `verify` calls
   `run-head-bound-proof.sh` exactly once and does not call
   `run-python-tests.sh` directly.
2. **No proof-script change.** The HEAD-bound runner continues to execute audit,
   report, and the default 21-gate proof graph.
3. **Provider inventory reflects direct calls.** GitHub no longer lists the test
   runner as a directly required provider script; GitLab remains unchanged.
4. **Environment policy remains on the job.** `ETHOS_TEST_WORKERS=2`,
   `ETHOS_TEST_TIMEOUT_SECONDS=300`, and `ETHOS_TEST_TIMEOUT_METHOD=signal`
   continue to flow into the nested unit gate.
5. **Failure remains visible.** No retry is embedded in the workflow. After
   publication, one explicit failed-job rerun is the maximum acceptance attempt.
6. **GitLab remains frozen.** Local GitLab files are not changed and no GitLab
   network request is made.

## Data Flow

```text
checkout -> bootstrap -> configure governed checkout -> arm admission
        -> OpenSpec strict validation
        -> run-head-bound-proof.sh
             -> ethos audit
             -> ethos report
             -> ethos prove --execute --expect-head
                  -> unit-architecture owner script once
                  -> remaining default proof gates
             -> compact HEAD/digest receipt
        -> upload proof/readiness artifacts (always)
        -> package job only when verify succeeds
```

## Error Handling

- Any gate failure keeps the proof receipt gapped and exits non-zero.
- Artifact upload remains `if: always()` so failure evidence is retained.
- Missing proof output remains an upload error.
- The architecture test fails if a future projection reintroduces the direct
  test step or removes the single proof entrypoint.

## Testing

1. TDD RED: add the single-execution architecture expectation against the
   unchanged workflow.
2. TDD GREEN: update template, projection, and direct-script inventory.
3. Focused provider projection tests, template consistency, Actionlint, strict
   OpenSpec validation, Claim validation, and quality audit.
4. Generic parity refresh when required.
5. One exact-HEAD full `ethos prove --execute`.
6. Land, accepted closeout, lane retirement, GitHub publication, then one bounded
   main failed-job rerun and exact run/branch observation.

## Rollback

Restore the direct test step and GitHub script inventory only if the single proof
entrypoint fails to produce its expected JUnit, coverage, or receipt artifacts.
Rollback restores the old duplicate execution; it does not establish that design
as efficient or contention-safe.
