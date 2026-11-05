# Proposal

## Why

An adopter cannot publish or record a receipt for a release tag that it released under an earlier
ETHOS. Publication admits the tag's original proof only if the running runtime compiles the same
policy for the old source today. Once a runtime changes that policy, every historical release tag
refuses with `proof_attestation_repository_policy_mismatch`, also when every peer already holds the
tag:

- AIGW's `v0.3.4` and `v0.3.5` (task 1.2.3 of its `gitlab-peer-reconciliation`);
- ETHOS's own `v0.2.0-alpha.8`, which exists only locally and on GitLab.

Re-proving an old source under today's policy fails on obligations it predates. This returns task
13.4.10 of `publication-history-repair`, which DR-0016 withdrew as in-repo work.

## What Changes

- A release tag whose completed `release.promote` effect created the exact tag object is qualified
  by the passing proof that effect bound. Publication admits that proof as recorded:
  - the copy that the release effect embeds verifies as the content-addressed attestation it
    names, so the proof's set member, whose lifetime may have ended, is not read;
  - its schema, subject, plan head, live tree and artifact custody verify under the current
    runtime;
  - its policy closure hashes to its recorded policy digest.

  It is never judged against the policy the current runtime compiles for the old source.

- Identity and publication facts are still checked now: the tag object, its name, its signature
  under the trust anchor in force, the declared target policy and each peer's exact ref.
- The rule covers every publication of such a tag: a peer that holds it, misses it or lags. A
  branch, and a tag without a release record, keep the current policy.
- A request that changes no peer still goes through admission, and its result reports
  `remote_push: already_applied` instead of `applied`.
- DR-0018 records the principle: a historical artifact is judged by the attestation made when it
  was produced.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: publication of a release tag reads its recorded qualification.

## Impact

- `src/ethos/adapters/mutation/proof_admission.py` and `proof.py`: a recorded admission of one
  bound proof.
- `src/ethos/adapters/repo/release.py`: the release record's bound proof for every release.
- `src/ethos/adapters/admission/publication.py`, `src/ethos/domain/publication/inspection.py`,
  `src/ethos/adapters/mutation/publication/execution.py`: one selection at every admission.
- `src/ethos/domain/publication/operation.py`: the no-push report.
- `docs/decisions/dr-0018-historical-artifact-attestation.md`, the decision index, the
  `repository-governance` spec and the changelog.
