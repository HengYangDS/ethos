---
subject: ethos:decision:historical-artifact-attestation
role: decision
state: canonical
decision_id: DR-0018
decision_status: accepted
relations:
  current_owner: ../../openspec/specs/repository-governance/spec.md
---

# DR-0018: A Historical Artifact Is Judged by the Attestation Made When It Was Produced

Status: canonical rationale. The repository governance specification owns current behavior.

Date: 2026-11-05.

Purpose: preserve why ETHOS publishes a release tag on the qualification its own release record
bound, and why a later runtime never re-judges that qualification under its own policy.

See also: [DR-0013: Historical repair evidence reads its own policy location](dr-0013-historical-repair-policy-location.md),
[DR-0016: Changes close on their delivered scope](dr-0016-change-closure-scope.md), the
[repository governance specification](../../openspec/specs/repository-governance/spec.md) and the
`adopter-tag-receipts` OpenSpec Change.

## Context

A release is qualified once: `release.promote` admits a passing proof and embeds it in the release
effect that creates the tag. Every later publication of that tag admitted the proof again, against
the policy the running runtime compiled for the old source. Once a runtime changed that policy,
every historical release tag refused with `proof_attestation_repository_policy_mismatch`, even when
every peer already held the exact tag object. Re-proving fails on obligations the source predates.
AIGW could not record receipts for `v0.3.4` and `v0.3.5`, and ETHOS could not publish its own
`v0.2.0-alpha.8` to GitHub.

DR-0013 already decided that historical repair evidence is read under the policy location its own
source declared. Release qualification was never brought under that rule. DR-0016 withdrew task
13.4.10 of `publication-history-repair` as in-repo work, to return as its own Change.

## Decision

A historical artifact is judged by the attestation made when it was produced.

- **Identity and publication facts are observed now:** the tag object, its name, its signature
  under the trust anchor in force, the declared target policy and each peer's exact ref.
- **Qualification is the attested fact from that time.** A release tag whose completed release
  effect created the exact tag object is qualified by the passing proof that effect bound. ETHOS
  verifies the copy the release effect embeds, which is the content-addressed attestation made at
  that time, under the current runtime: its identity, schema, subject, plan head, live tree,
  artifact custody and recorded results, and that its policy closure hashes to its recorded policy
  digest. It does not read the proof's set member, whose lifetime ends once no ref or tag pins the
  commit.
- **No later re-judgment.** ETHOS does not compile today's policy for the old source, does not
  re-evaluate dependency acceptance against today's advisories and does not recompile its
  Commitment. There is no policy-version floor: the floor is verifiability, and anything that
  cannot be verified refuses by name.
- **Scope.** Branches, and tags without a release record, keep the current policy.

## Alternatives Rejected

- **Effect-free observation, no proof when no peer changes:** rejected because a tag whose original
  proof is missing would publish, a lagging peer would still meet today's policy, and it weakens the
  requirement that an already-applied claim is freshly admitted.
- **Re-prove the old source under today's policy:** rejected because a source cannot meet
  obligations it predates, and it re-judges accepted history.
- **Ask the original runtime to recompile:** rejected because a proof does not record its runtime,
  old installations are retired, and every publication would run old code.
- **Ignore the mismatch for tags:** rejected because it drops the check without a replacement.

## Consequences and Boundary

- A release qualified under an earlier, weaker policy stays publishable to new peers. Its receipt
  names the proof and its policy digest; a consumer that wants today's bar releases a new identity.
- Loss of the release record or of the proof's artifact makes the tag unpublishable. This fails
  closed.
- The 0.3.0 channel model's qualification attestations rest on this rule: a channel move reads a
  build's attestations as recorded.
- Other historical re-derivations, such as a maintenance range under today's commit policy, move to
  the same record if one is found failing, never to a special case.

## Evidence and Revisit

- The `adopter-tag-receipts` and `mapped-release-retag` Change proposals and designs record the
  incident: a repaired release tag could not publish under a later runtime's policy, and once its
  tag moved, the attestation set no longer held the proof.
- Publication tests verify the embedded proof on the original commit under a later runtime, refuse
  a missing or altered embedded proof, and publish a re-created tag only through its mapped-retag
  receipt. Mutation checks that remove each refusal make those tests fail.

Revisit when a release record changes what it embeds, or when ETHOS starts retaining proofs
independently of tags. Retire this record when the repository-governance specification itself
states these alternatives and limits.
