+++
title = "A refused proposal retirement names itself as the next step, not the publication it needs"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Give the retirement the landed head (`--expect-head <head>`), and publish the accepted branch to the peer first: `ethos publish --ref refs/heads/dev --probe-remote --expect-head <head> --json`, then its receipt."
+++

`ethos publish --retire --ref refs/heads/proposal/<name> --probe-remote` without a head answers
`expect_head_required`. With the head, while the peer's accepted branch does not yet hold the
proposal's commit, it answers `proposal_retirement_peer_not_accepted:<peer>:<ref>`. Both results
name the retirement's own probe as the next step; neither names the publication of the accepted
branch that the second one needs. Measured in a temporary repository with the candidate of
`ca4a7fb62` on 2026-11-23.
