## Context

The July 24 timeout-resilience change replaced abrupt thread-mode worker exit
with a finite 300-second signal timeout while retaining four GitHub workers. At
that time a complete 2,954-test replay supported the four-worker decision. The
suite has since grown to 3,557 tests and the accepted GitHub `main` run for
`626ab408d` produced two incompatible failure sets across two attempts:

1. two unrelated Git-backed tests blocked in `git update-ref` and `git rev-list`
   communication until the 300-second ceiling; and
2. two different source-budget tests failed, one because a supervised worker
   reached `timeout` instead of `output_exceeded` and one at an explicit
   two-second test ceiling.

The same four tests passed in a complete two-worker replay at accepted commit
`8555afde7`. The run reached 3,556 passes and failed only the lane-governance
contract that requires an active Claim. That diagnostic is not final proof, but
it isolates worker count as the smallest provider-specific control available.

Pre-implementation owner-gate validation also found two accepted MD032 failures
in the snapshot replay absorption implementation plan: each `**Files:**` label
was immediately followed by a list without the required separating blank line.
Those accepted errors block GitHub quality before repository proof. Adding the
two blank lines changes no prose or behavior and is therefore a bounded baseline
prerequisite rather than a Markdown policy change.

## Goals / Non-Goals

**Goals:**

- Bound simultaneous subprocess and Git pressure on the self-hosted macOS
  repository-proof runner.
- Preserve parallel test execution with two workers.
- Preserve the validated 300-second signal timeout and ordinary pytest failure
  reporting.
- Require exact-HEAD local proof and fresh exact-SHA GitHub evidence before
  claiming the change complete.

**Non-Goals:**

- Masking a deterministic product defect or accepting a failed rerun.
- Editing per-test timeout markers or the source-budget worker resource profile.
- Changing GitLab while it is unreachable from the current network.
- Treating local proof as hosted publication evidence.

## Decisions

1. **Reduce GitHub repository proof to two workers.** Two workers retain xdist
   parallelism while halving concurrent subprocess, temporary-repository, and
   Git-lock pressure relative to the four-worker projection.
2. **Keep timeout policy unchanged.** `ETHOS_TEST_TIMEOUT_SECONDS=300` and
   `ETHOS_TEST_TIMEOUT_METHOD=signal` remain paired and validated by the owner
   script. Worker-count reduction and timeout observability solve separate
   problems.
3. **Change the canonical template and generated projection together.** The
   provider YAML remains declarative, and projection-drift checks continue to
   prevent one surface from becoming an independent policy owner.
4. **Do not patch individual tests.** The two hosted attempts implicated four
   different tests, while the two-worker replay passed all four. Raising their
   limits would hide runner contention without addressing its shared cause.
5. **Do not add blind retries.** A retry may provide diagnostic evidence but
   cannot turn a failed exact-SHA run into acceptance evidence.
6. **Freeze GitLab activity.** GitLab remains one-worker and unmodified. Its
   current hosted state is explicitly unverified until intranet access returns.
7. **Close the exact accepted Markdown prerequisite.** Add only the two missing
   blank lines observed by the owner gate. Do not reformat or rewrite the plan.

## Risks / Trade-offs

- **Hosted proof may run longer** -> retain two workers rather than serializing;
  measure the exact-SHA GitHub run before closeout.
- **Contention may still occur** -> require a fresh no-retry GitHub run and keep
  failure visible rather than weakening individual test contracts.
- **Accepted base may advance concurrently** -> refresh the owned lane, rerun
  parity, and produce a new exact-HEAD proof before landing.
- **GitLab evidence remains incomplete** -> separate GitHub publication from
  dual-remote completion and record GitLab as deferred, not passing.

## Migration Plan

1. Bind this Work Lane to its bounded Claim.
2. Change the architecture expectation to two workers and observe RED against
   the unchanged four-worker workflow.
3. Add the two admitted Markdown blank lines, then update the canonical GitHub
   template, generated workflow, and quality spec.
4. Run focused contracts, Markdown lint, strict OpenSpec checks, a complete two-worker gate,
   parity, and exact-HEAD ETHOS proof.
5. Archive, refresh if needed, land, close out, and retire this owned lane.
6. Publish GitHub `dev` then `main` serially and require exact-SHA ETHOS CI plus
   CodeQL evidence. Leave GitLab frozen.

Rollback restores the prior four-worker GitHub projection and keeps hosted
readiness explicitly blocked; it does not imply that the prior projection is
healthy.

## Open Questions

None. Hosted results remain evidence and cannot be predicted by this design.
