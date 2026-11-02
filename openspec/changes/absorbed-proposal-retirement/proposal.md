# Proposal

## Why

A Work Lane publishes `proposal/<lane>` to every peer so hosted CI verifies it before landing, and
nothing in its later life retires that ref. `land`, `land --closeout` and `lane retire` move only
local refs, and the next action of a successful `ethos publish` of `dev` is empty, so the cleanup
depends on someone remembering `ethos publish --retire` for each peer. The 11-02 landing shows the
gap: GitHub's proposal was retired by hand after `dev` reached it, and GitLab's was refused with
`proposal_retirement_peer_not_accepted` because GitLab's `dev` was published later, after which
nothing named it again.

Retirement is admissible exactly when a peer's accepted branch preserves the proposal tip, which is
the moment that peer receives `dev`. The publication that causes it can say so.

## What Changes

- After a publication of the accepted branch applies, its result lists, for each peer whose
  accepted branch it moved, the proposal refs whose exact tips the published head preserves, judged
  by the same contribution observer that retirement uses.
- Its next action becomes the existing retirement probe of exactly those refs on those peers, so
  every retirement gate still applies, including the open-review check.
- A peer whose proposal listing is unavailable is named as unobserved; the publication's own state
  and verdict do not change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: accepted publication names the proposals it absorbed.

## Impact

`src/ethos/adapters/mutation/publication/`, `src/ethos/domain/publication/operation.py` and the
publication retirement tests. One bounded `git ls-remote` per peer after an applied accepted
publication. No new command, effect, receipt field or adopter configuration.
