---
subject: ethos:ownerless-dirty-ancestor-semantic-closeout-20260724:20260721-gitleaks-cache-resilience
role: evidence
state: active
event: lane_resolution/preserve-retire
target_branch: work/20260721-gitleaks-cache-resilience
target_head: ffe5bf56719a2e218d74ac1a3fd35ebe777f5136
claim: ownerless-dirty-gitleaks-cache-resilience-20260724
---

# Dirty ownerless closeout: 20260721 gitleaks cache resilience

## Exact observation

The source is a linked, dirty, missing-lease, claim-free accepted ancestor at
`ffe5bf56719a2e218d74ac1a3fd35ebe777f5136`. Its tracked binary diff is 3,406
bytes with SHA-256
`0b73ff784df4277ab90a70063074fe9243ad4162ed11a104dfaca52c083d20d4`.
The working test blob is
`5cc39962b47d5a7d44d31e9b27f36c0ef2d8b062`; the working installer blob is
`91660534f01d2094aec27f417d3096ff0988aba2`.

## Exact absorption

Both working blobs entered accepted history together in
`408e06eeadae7326ada2fc4f468612971b35031a` (`fix(ci): persist verified gitleaks
artifacts`). The installer remains byte-identical at accepted baseline
`266018e9832866c00499bd5bcbf4dfa9cc831d89`; the architecture-test file has only
been extended by later accepted coverage. Its focused accepted test passes.
This is exact historical blob absorption, not inference from lane age.

## Bound decision

After this carrier is accepted, native resolution may select only
`work/20260721-gitleaks-cache-resilience` with disposition `preserve-retire`.
It must preserve the dirty patch in a verified recovery package before removing
the source ref and worktree. Any head, blob, lease, claim, or occupancy drift
blocks the effect.
