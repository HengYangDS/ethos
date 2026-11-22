# Design

## Context

`issue_proof_attestation` writes a proof record whose body holds the whole `TransitionPlan`. The
Attestation set refuses a member above 1 MiB when it is added. A plan grows with the lane's
changed paths, so a large lane's proof passes its gates and loses its record. The landing's
integration and acceptance records embed the proof, so they grow with it.

The proof's checks already live outside the record: each is a content-addressed file under
`ethos/artifacts/`, cited by digest. The plan is the one large part still carried by value.

## Goals / Non-Goals

**Goals:**

- A proof record of any lane stays within a third of the bound, and the bound does not move.
- A cited plan is exactly the plan the proof ran: its bytes are addressed by the plan's own digest.
- Every way the cited bytes can be wrong is refused under its own gap code.
- Records written by a released runtime stay readable and selectable.

**Non-Goals:**

- A new envelope for the record. The DSSE form is a later Change.
- Making a rollback release able to admit a cited proof.
- Changing the 1 MiB bound or the set's requirement.

## Decisions

- **Two predicates, one reader.** `proof:execution` carries the plan by value;
  `proof:execution-digest` cites it. `plan_from_statement` accepts both and takes the repository
  root, which it needs to find the artifact store.
- **The writer cites only what it cannot carry.** A record is written in the cited form when
  the record that carries its plan would pass a third of the member bound, and in the carried
  form otherwise. A third, because a landing's record carries the proof once and a release's
  record twice, and each must fit the bound: in the 37 release records of this repository's
  own set, a record is two proofs and about 12,000 bytes. The reason for keeping the carried
  form is the landing of this change itself: a repository's hook admits a landing with the
  runtime built from its accepted branch, which selects `proof:execution` only until this change
  is accepted there. So no record that could be written and released before changes its form in
  this release. A later Change writes the cited form always.
- **The plan file is a proof artifact.** `write_plan_artifact` writes the plan's canonical JSON,
  without its `digest` field, through `write_content_addressed` into the store the checks use. The
  file's SHA-256 is the plan's digest, which the record's envelope already binds. It is not
  custody: custody follows a selection, and the plan follows its proof.
- **Fail closed by name.** An absent file is `proof_attestation_plan_artifact_missing`; other bytes
  are `proof_attestation_plan_artifact_digest_mismatch`; a write that would replace other bytes is
  `proof_attestation_plan_artifact_collision`; bytes that match the digest and are not a plan
  are `proof_attestation_plan_invalid`, the code a malformed embedded plan already has.
- **Written at each issuance.** The record is issued again at prove, at archive and at landing,
  and each issuance of a cited record writes the plan it cites. A landing can leave more than
  one plan file.
- **Retention knows the kind.** A file of the artifact store that reads as a plan is `proof-plan`:
  kept while a record cites it, deleted when its proof leaves.
- **Selection is by record.** Two proofs of one head are not both admitted to one set, whatever
  their form.

## Risks / Trade-offs

- A rollback to a release before this one cannot prove a large head: it does not admit the cited
  proof and its own record is refused by the bound. Measured at 1,404 changed paths; below the
  bound a rollback's own proof should work and was not measured.
- The store gains one plan file for each issued record, about 1.2 MB at 1,404 changed paths. A
  released runtime leaves those files in place.
- The plan reader gains a parameter at thirteen call sites of the product. `proof.py` keeps one
  line under the per-file ceiling.
- No release of a lane whose proof is just under a third of the bound is run. The two sides of
  the threshold are tested on the writer, and a release record's size is arithmetic on the
  measured records.
- Two forms are written until the later Change. A record between a third and half of the bound
  is cited although a landing could carry it.
