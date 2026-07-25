## Context

The GitHub repository-proof job now has one authoritative full-test path:
`run-head-bound-proof.sh` invokes `ethos prove --execute --expect-head`, and the
default proof graph invokes the unit-and-architecture owner gate once.

The owner script currently orders its producers as:

```text
audit -> report -> prove -> combine(audit, report, proof)
```

That order is invalid in a clean runner because report consumes state produced
by proof: coverage XML and the exact-HEAD executed-proof receipt. GitHub dev run
`30172606031` made the defect observable. Audit was clean, the 21-gate proof was
proven at the expected HEAD, and JUnit recorded 3,558 passing tests, while the
earlier report remained gapped for missing coverage and proof state. The final
receipt correctly rejected that inconsistent bundle.

The old duplicate standalone test step happened to produce coverage before this
script ran. Its removal did not create the ordering defect; it removed the
accidental producer that concealed it.

## Goals / Non-Goals

**Goals:**

- Make report observe proof-produced artifacts from the same script execution.
- Preserve one and only one full proof graph per hosted repository-proof job.
- Preserve exact-HEAD binding, audit, compact receipt semantics, failure
  diagnostics, and always-retained readiness/proof artifacts.
- Require a fresh exact-SHA hosted run before claiming the GitHub branch green.

**Non-Goals:**

- Changing proof semantics, reusing external receipts, or weakening any gate.
- Adding a retry, increasing timeouts, changing xdist workers, or adding a host
  lock.
- Changing the GitHub workflow or any GitLab file or hosted state.

## Approaches Considered

### A. Reorder report after proof — selected

Use the existing producers in dependency order:

```text
audit -> prove -> report -> combine(audit, report, proof)
```

This is the smallest correction. Proof still runs once. Report then reads the
coverage and proof state created at the exact expected HEAD. If proof fails, the
script still runs report and retains a post-execution scorecard before returning
the proof or receipt failure.

### B. Restore the standalone full-test step — rejected

This would mask the defect again by recreating coverage before report, while
reintroducing the duplicate 25-minute test graph the predecessor intentionally
removed. It adds work without an independent trust boundary.

### C. Retry the failed hosted job unchanged — rejected

The observed report was generated before proof by deterministic script order. A
retry cannot make a clean checkout contain proof-produced artifacts before the
proof executes.

### D. Ignore report when proof passes — rejected

The compact receipt intentionally requires audit, report, and proof to agree.
Weakening that conjunction would hide real readiness gaps rather than fixing the
producer dependency.

## Decisions

1. Audit remains the first read-only repository check.
2. `ethos prove --execute --expect-head` runs exactly once before report.
3. Report runs after the proof attempt, including after a non-zero proof result,
   so retained artifacts describe post-execution state.
4. The final receipt remains `ok` only when audit, report, and proof are all
   `ok=true`; proof exit status retains precedence on failure.
5. GitHub still has no separate direct test step and no embedded retry.
6. GitLab remains frozen and byte-unchanged.

## Data Flow

```text
checkout -> bootstrap -> run-head-bound-proof.sh
  -> audit.json
  -> prove --execute --expect-head
       -> unit-architecture once
       -> coverage.xml + junit.xml
       -> executed-proof.json
  -> report.json reads same-HEAD coverage and proof state
  -> compact receipt combines audit + post-proof report + proof
  -> artifacts uploaded always by the existing provider workflow
```

## Error Handling

- A proof failure is captured without aborting before report runs.
- Report and compact-receipt failures remain visible and non-zero.
- Proof diagnostics are printed from retained stderr on failure.
- Missing or malformed audit, report, or proof JSON keeps the receipt invalid.
- No retry converts a failure into acceptance.

## Testing

1. TDD RED: execute the unchanged real owner script with a controlled fake `uv`
   whose report is green only after proof; require a zero exit and exact
   `audit -> prove -> report` call order.
2. TDD GREEN: move only the report invocation after the proof attempt.
3. Run the focused behavioral test, all provider projection tests, shell lint,
   quality audit, strict OpenSpec validation, Claim validation, and changed-scope
   planning.
4. Refresh generic parity only after foreign overlapping activity has naturally
   cleared or candidate refresh makes it safe.
5. Run one exact-HEAD full ETHOS proof, archive officially, re-prove archive HEAD,
   land, close accepted root, retire the owned lane, then publish GitHub dev.
6. Publish main only after the exact dev SHA is green.

## Rollback

Revert the three-command order only if post-proof report execution itself
corrupts or removes proof evidence. Do not restore the redundant standalone test
step as a workaround; keep hosted readiness blocked until a separately governed
replacement preserves one full proof and a consistent receipt.
