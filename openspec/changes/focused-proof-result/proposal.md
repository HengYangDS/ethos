# Proposal

## Why

A focused proof reports evidence as unproven that it never examined. Two cases, both read in the
source on `dev` at `d98081605` and both met by governed repositories' sessions:

- `ethos prove --execute --gate <ids>` whose Commitment requires an axis that the selection does
  not cover is refused before any gate, as `gapped` with `quality_obligation_unproven:<axis>`. The
  result has no field that says no selected gate ran. One session read it as a result of its gate
  and met the gate's failure only in the full proof, after a queue wait.
- `ethos prove --host --execute --gate <ids>` without `--full` and without `--expect-head` binds
  no source tree and still judges the results against it. Every gate passes and the run reports
  `source_integrity_unproven:<path>` and `quality_obligation_unproven:<kind>`. With
  `--expect-head` the same command passes. It cost one session two proof rounds.

## What Changes

- An executing host run binds the current tree, or refuses a focused run without an exact head by
  name. It never reports evidence as unproven that it did not bind.
- A refusal before the gates states that nothing was executed and names the selected gates as not
  run, and its next action names the form that runs them.
- Regressions for both cases.
- The names of the gates that did not run go in `data.not_run`, the field that
  `host-ticket-release` gave a host proof whose admission is refused. Two cases that repair
  left: a full proof whose admission is refused still drops the results of the readiness
  gates that ran, and a host proof asks for its host ticket after a readiness gate failed.
  A third: when a run's gates have ended and its place in the queue cannot be given up, a
  host proof reports no check, and `ethos host run` reports no status of its command.
- Candidate from the release lane's own tools, where an interrupted test run was recorded as
  passed on 2026-11-15: a gate's result states the wrapped tool's exit status, and "interrupted"
  is a named state that never reads as a pass.
- Cost of the first case, reported by a governed repository's session on 2026-11-19 under
  0.2.0-beta.10: a focused run of its static gate alone was refused before any gate, the session
  read that as "this gate cannot run before a proof", and a full proof then waited 3,228 seconds
  in the host queue for a refusal that the static gate gave in 41 seconds. The readiness run
  existed and held that gate. So the refusal's next action names
  `ethos prove --readiness --execute`, and the readiness answer names where the list of gates
  that ran is kept when the answer is bounded.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The proof's host path and its focused plan, with their tests. It narrows what a result may claim
and adds no refusal to a command that passes today.

Owner: the release lead. Next action: write the patch and measure it. Read again: at the cut of
0.2.0-beta.12.
