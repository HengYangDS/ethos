# Design

## Boundary

The mechanism is intentionally narrow. It only handles unmerged paths matching
`evidence/parity/*-shadow.json`. Those files are tracked evidence projections
whose contents bind to a HEAD and semantic digest; a replayed lane cannot make an
old projection true by choosing either side of the conflict.

## Resolution

When `git rebase candidate/dev` fails, ETHOS checks the unmerged path set:

1. If every unmerged path is a parity shadow evidence projection, ETHOS checks out
   the candidate version and continues the rebase.
2. The command returns `base_refreshed_projection_stale` and records:
   - `projection_refresh_required = true`
   - `projection_refresh_gaps`
   - `stale_projection_paths`
   - next actions to regenerate parity evidence and rerun head-bound proof.
3. If any unmerged path is outside that projection set, ETHOS aborts and returns
   the existing `refresh_base_failed` gap.

This preserves semantic conflict visibility while letting generated projection
state be regenerated from the new repository truth.
