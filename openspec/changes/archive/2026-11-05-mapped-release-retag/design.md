# Design

## Context

See [proposal.md](proposal.md). AIGW asked for this on 2026-11-05 as a second Change in the
`adopter-tag-receipts` lane. A completed signature repair (`completed_signature_repair`) yields a
verified old-to-new commit mapping and the repair attestation's id. A history repair also binds a
verified backup bundle that holds every original object. Release tags are created by
`create_signed_tag` in an owned staging store and moved by `execute_git_effect` under an exact ref
intent. The reference-transaction hook admits a `release.tag` move only with that intent.

## Goals / Non-Goals

Goals:

- Re-create a repaired release tag on its replacement commit with the original tag's name, tagger,
  date and message; only its target and signature change.
- One attestation per re-tag, and publication on the original release's qualification.

Non-goals:

- Re-tagging a commit that no completed repair replaced. The mapping is the only authority.
- Re-judging the original release under today's policy (DR-0018).
- Moving a tag ref that already points at anything other than the original object.

## Decisions

1. **Owner.** The re-tag sits beside `promote_release`, in `adapters/mutation/accepted/retag.py`,
   and reuses its staging, plan and effect primitives. It is reached through `ethos land --retag`,
   so the public command plane keeps its six workflow commands.
2. **Mapping.** For each original tag target, the completed repair whose mapping contains that
   commit is resolved through the existing repair readers. Its attestation id is the
   `mapping_attestation_id`. A target outside every completed mapping refuses as
   `release_retag_target_not_mapped`. A repair record that fails validation refuses as
   `release_retag_mapping_unverified`.
3. **Original object.** The tag object comes from `--original-tag <tag>=<oid>` or the local ref,
   and must be an annotated tag named `<tag>`. When it was pruned locally, it is restored with
   `git bundle unbundle` from a completed history repair's backup bundle that lists it and still
   hashes to the digest its repair record bound. Unbundling writes objects only, and the object id
   authenticates the restored bytes. A missing object refuses as `release_retag_original_missing`.
4. **Re-creation.** The new object keeps every header line except `object`, and the message bytes,
   then is signed by the configured signer in an owned staging store. It must verify under the
   trust anchor in force (`release_retag_signer_untrusted`). Signing is never replayed after an
   interrupted attempt, as for release tags.
5. **Effect.** One exact compare-and-swap per tag ref, from absent or from the original object. A
   ref that points at anything else refuses as `release_retag_name_occupied`. The plan's transition
   is `release.retag`, which the executor and the reference-transaction hook resolve to
   `release.tag`, admitted by the plan's own ref intent.
6. **Receipt.** One `release:mapped-retag` attestation per re-tag binds the old tag object, the new
   tag object, the mapping attestation id and the mapped target. It mints no authority. Its
   lifetime, and that of the tag move's effect record, is the tag's lineage, like the release
   record's.
7. **Batch and digest.** A request names several tags. The preview reports one plan digest over
   every admitted re-tag, and apply requires it (`release_retag_plan_digest_mismatch`). Each
   refused tag is listed by name with its gaps. Apply proceeds only when no tag is refused, moves
   the tags one at a time and records each receipt with its move, so an interrupted batch leaves
   no re-created tag without its receipt.
8. **Publication.** For a tag without a release record whose one `release:mapped-retag` receipt
   binds the exact object, the publication reads re-verify the receipt's mapping against the
   completed repair records, then read the original tag's release record with the mapped commit as
   its accepted-history witness. The proof that record embeds is admitted as recorded on the
   original commit (`adopter-tag-receipts`, decision 2). Its set member is not needed: it ends once
   the tag moves off the original commit. The admission report names the commit the proof attests.
   Without the receipt, the tag has no release record and keeps the current policy.
9. **Report.** `land --retag` reports in the shape of `land --release`: `ready_to_retag` with the
   apply command as the next action, then `retagged`. It refuses beside `--release`, `--closeout`
   or `--candidate-head` (`release_options_conflict`) and on a malformed `--original-tag`
   (`release_retag_original_tag_invalid`).

## Risks / Trade-offs

- The original tag object must survive locally or in the repair's backup bundle. If both are gone,
  the tag cannot be re-created; this fails closed.
- Re-verifying the mapping reads the pre-repair commits. Once they are pruned and not restored,
  the re-created tag can no longer be re-tagged or published; this fails closed.
- A peer that already holds the original tag object is not changed by this Change; replacing a
  published tag is a separate decision.
- A tagger date in the past is reproduced exactly; the receipt and signature record when ETHOS
  re-created the object.
