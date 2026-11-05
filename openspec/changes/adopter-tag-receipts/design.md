# Design

## Context

See [proposal.md](proposal.md). The design was reviewed by AIGW, the consumer, on 2026-11-05 under
the user's delegation, and decided by the ETHOS session the same day. The research lives in the
session's design draft; its decisions are carried here.

Publication of a `release_publication` tag selects `repository_transition` proof. The proof head is
the tag's peeled commit when the tag's completed `release.promote` effect created that exact object.
Proof admission then compiles the policy the running runtime derives for that old source
(`resolve_proof_policies`) and admits a proof only if its recorded policy equals one of those
compiles. The release effect already embeds the proof it admitted
(`accepted/release.py`, `prior_attestations.proof`).

## Goals / Non-Goals

Goals:

- A release tag with a release record is qualified by its bound proof, admitted as recorded, at
  every admission: the publication context, push admission, the pre-push hook and the executor.
- Every refusal is named and happens before any peer changes.

Non-goals:

- Repairing tags whose peers name different objects (task 13.4.9, `forge-admission-and-assurance`).
- Re-deriving other historical facts, such as a maintenance range under today's commit policy.
- Multi-source requests: one request has one source object
  (`contracts/publication.py`, `publication_target_source_mismatch`).

## Decisions

1. **Option B, original-policy proof.** AIGW chose it over effect-free observation, which would
   publish a tag whose original proof is missing and weaken the fresh-admission requirement.
2. **Recorded admission.** `proof_attestation(..., recorded=<embedded proof>)` selects exactly the
   bound ID and requires the set member to equal the embedded copy
   (`release_qualification_binding_mismatch`). It then runs the integrity stages as today: subject,
   plan head, live tree, archive scope, artifact custody and statement results. Instead of
   comparing with today's compile, it requires the recorded policy closure to hash to the recorded
   digest (`proof_attestation_recorded_policy_inconsistent`). It repeats no judgment that moves with
   time or runtime: no policy compile, no dependency acceptance and no Commitment recompile. A
   missing member refuses as `release_qualification_missing`. This is AIGW's answer 5: the floor is
   verifiability under the current runtime, with no policy-version floor.
3. **One release read.** `accepted_release_source` already reads the release record once per
   admission. It now returns `qualification` (the bound proof ID and its embedded copy) for every
   release record, beside the maintenance-only `release` binding. The publication context reads the
   record once through `release_publication_selection`, which also selects the proof head. The
   publication reads of a release (selection, qualification and the source baseline) move to
   `adapters/repo/release_publication.py`, so the release owner stays under the 500-line ceiling, and
   the proof's own integrity stages move to `adapters/mutation/proof_record.py`, which both the
   current and the recorded admission share.
4. **The destination derives the mode.** `publication_proof_admission` uses the recorded admission
   only for a repository-transition target that carries a release qualification. A caller cannot
   select it, and a branch or a tag without a release record keeps today's rule.
5. **Receipt.** No new field (AIGW answer 1). `publication:remote-effect` records each peer's
   observed tag object, and its plan binds the release-bound proof's ID as `prior_attestations`.
   When every attempt is `already_applied`, the result reports `remote_push: already_applied`.
6. **Scope of a batch.** AIGW's batch (`v0.4.9` to `v0.6.0`, answer 3) is one request per tag, each
   judged by its own release proof. A tag without a passing release-bound proof refuses by name in
   its own result, never skipped.
7. **Peers.** For `v0.3.5`, only GitLab is receipted, referencing the existing GitHub receipt
   `91f23827` (answer 2): the operator selects `--peer gitlab`.
8. **Acceptance.** AIGW accepts on the first release that ships this Change, with aigw-cli rebound
   to it (answer 4). ETHOS's own acceptance case is `v0.2.0-alpha.8` to GitHub.
9. **DR-0018** states the general rule and extends DR-0013 from repair evidence to qualification.

## Risks / Trade-offs

- A release qualified under an earlier, weaker policy stays publishable to new peers. The receipt
  names the proof and its policy digest; a consumer that wants today's bar releases a new identity.
- Custody loss of the bound proof or its artifact makes the tag unpublishable. This fails closed.
- Proof admission still runs other stages at the old source. They pass for the known cases; a
  failing one moves to the same release record, not to a special case.
