## Context

The archived `adopter-openspec-lifecycle-20260714` Change and its active claim
describe the same repository behavior that must be continued: `plan` and
`prove` evaluate official OpenSpec lifecycle for a valid adopter. The original
Codex worktree and checkout-local temporary evidence are absent. Repository
history and surviving session artifacts preserve meaning, but they cannot
recreate the original execution context.

The official OpenSpec lifecycle requires an active Change to have proposal,
design, tasks, delta specs, and an active claim whose carrier points to that
Change. Repository-governance further requires a continuation to retain the
historical carrier, bind the same episode claim, and re-observe current inputs
before a new proof or lifecycle transition.

## Design

This successor uses a new owned Work Lane from the current `candidate/dev`
baseline. It binds the existing `adopter-openspec-lifecycle-20260714` claim;
the claim's active carrier moves from the historical archive to this active
continuation, then to this continuation's archive at closeout. The predecessor
archive remains immutable historical evidence.

The successor Chronicle is a continuity packet, not a reconstructed session. It
records:

1. retained source identities and content digests;
2. the exact runtime state that is absent and therefore unrecoverable;
3. the current Work Lane, candidate, accepted, and historical-lane anchors;
4. a re-execution plan that proves current behavior on the successor HEAD; and
5. the limits of local proof, candidate integration, accepted-root closeout, and
   remote publication.

No implementation behavior is changed unless current re-execution finds a real
semantic drift. The existing behavior is first tested as it stands; a failure
would create a focused RED regression and minimal repair in this same carrier.

## Alternatives

- **Recreate the old host directory:** rejected. A directory with the same path
  would not recover its Git index, lease, temporary artifacts, or runtime state.
- **Reuse or merge the historical Work Lane:** rejected. It is foreign,
  unleased, and diverged from the current candidate baseline.
- **Create an unrelated claim:** rejected. The continuity requirement calls for
  the same episode claim to remain bound while a successor re-observes inputs.

## Proof Strategy

1. Validate the continuity packet's historical identities and current Git
   anchors before authoring.
2. Run focused generic-adopter lifecycle regressions on the successor baseline.
3. Complete the official active Change and validate it strictly.
4. Run `ethos plan --changed`, `ethos openspec --lifecycle --json`, and a
   HEAD-bound executed `ethos prove` on a stable committed successor HEAD.
5. Archive the completed Change, re-run the final HEAD-bound proof, then use
   only sanctioned local land/closeout commands if their fresh gates allow it.

The final proof is current command evidence. The Chronicle records its inputs
and boundary but never treats historic proof as proof of a later HEAD.
