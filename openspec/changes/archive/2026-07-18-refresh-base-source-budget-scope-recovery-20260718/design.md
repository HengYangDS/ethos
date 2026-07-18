## Context

`candidate/dev` contains the archived `quality:source-budget-proof-scope`
correction. Its carrier and claim make the candidate implementation authoritative
for the separation between fine-grained proof and global compression. The older
Work Lane change represents the same policy but has a different intermediate
read-model shape.

## Decision

A rebase resolver may retain candidate stage-2 content only if all conditions
hold together:

1. the unmerged path set exactly equals the three source-budget proof-scope
   implementation and regression files;
2. an archived claim with subject `quality:source-budget-proof-scope` binds an
   archived OpenSpec carrier whose promotion targets declare all three paths;
3. stage-2 scoring declares `global_compression_report`;
4. stage-2 report projects that global compression into the scorecard; and
5. stage-2 regressions prove source-budget is excluded from the default graph
   but remains in the full graph.

The resolver checks these facts from the current replay tree and Git index, then
uses the candidate version only for that exact conflict set. Any missing fact
returns no resolution and preserves ordinary fail-closed behavior.

Generated parity projections and this semantic recovery may occur in the same
replay. Only `projection_regeneration_required:*` makes the refresh result a
stale-projection state and populates `stale_projection_paths`. The exact
source-budget paths remain in separately named semantic-recovery diagnostics.

The default proof remains the fine-grained admission floor. The full proof
retains `source-budget` as global compression evidence; it must not be treated
as local code correctness.

## Consequences

This does not turn a generic conflict preference into a policy. It recognizes a
prior, archived, evidence-bound policy correction and retains the candidate's
more complete representation. Proof and source-budget validation remain
required after the refreshed lane reaches a new HEAD.
