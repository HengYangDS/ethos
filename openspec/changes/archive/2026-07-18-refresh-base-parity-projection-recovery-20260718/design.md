## Context

A parity shadow is generated evidence. During rebase, Git can have a stage-0
resolution for its exact path while `git diff --diff-filter=U` still reports the
conflict. This happens with a prior `rerere` resolution and must not be confused
with a raw worktree merge-marker file.

## Decision

Inspect the index stage-0 payload before the existing checkout-and-add fallback.
Admission requires all of the following:

1. every conflicted path is directly under `evidence/parity/` and ends in
   `-shadow.json`;
2. the stage-0 blob parses as JSON;
3. `schema_version` is `1`; and
4. its `adopter` exactly equals the adopter encoded in that path.

When those conditions hold, preserve the staged projection, continue the
rebase, and expose `projection_regeneration_required:parity:<adopter>`. Any
other condition falls through to the existing candidate-side projection reset or
fails closed as a real source conflict.

## Consequences

The mechanism trusts neither a file suffix nor arbitrary staged JSON. It still
requires fresh shadow evidence and a new HEAD-bound proof after a successful
refresh. No source conflict is silently merged.
