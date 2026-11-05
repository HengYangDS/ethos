# Proposal

## Why

An adopter whose history was repaired natively with `ethos lane repair-signature` still has signed
release tags on the commits the repair replaced: 72 for aigw-cli, and more for the proxy. ETHOS
admits a new tag only on the current accepted head, and a raw `git tag` is excluded, so a historical
tag cannot be re-created on its replacement commit through ETHOS. AIGW asked on 2026-11-05 for one
native mapped re-tag. Under DR-0018 it carries the release's original qualification through the
repair's mapping.

## What Changes

- `ethos land --retag <tag>` previews, and with `--apply --authorize --expect-plan-digest <digest>`
  applies, a batch of re-tags. For each tag it:
  - reads the original tag object, by `--original-tag <tag>=<oid>` or the local ref;
  - maps its target through the completed signature repair that replaced it;
  - creates a signed annotated tag on the mapped replacement commit, with the original name,
    tagger identity, date and message bytes. Only the target and the signature change;
  - moves the tag ref by exact compare-and-swap, from absent or from the original object;
  - records one `release:mapped-retag` attestation that binds the old tag object, the new tag
    object, the mapping attestation id and the mapped target.
- Refusals are named for each tag, and a batch never skips one:
  - `release_retag_target_not_mapped`;
  - `release_retag_mapping_unverified`;
  - `release_retag_original_missing`;
  - `release_retag_name_occupied`;
  - `release_retag_signer_untrusted`;
  - `release_retag_plan_digest_mismatch`.
- Publication accepts a re-created tag through that chain: its qualification is the proof that the
  original tag's release record embeds, carried over by the mapping, which applies
  `adopter-tag-receipts` once more. The original proof's set member, which ends once the tag
  moves, is not needed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: a repaired release tag is re-created on its replacement commit, and
  publishes on its original qualification.

## Impact

- New `src/ethos/adapters/mutation/accepted/retag.py`, beside the release mutation.
- `src/ethos/surface/cli/root/land.py` and `src/ethos/domain/land/operation.py`: the `--retag`
  request.
- `src/ethos/adapters/repo/release.py` and `release_publication.py`: the mapped qualification for
  publication; `src/ethos/adapters/admission/git_admission.py`: the hook admits the planned move.
- `src/ethos/adapters/repo/attestation_lifetime.py`: the receipt's lineage lifetime.
- The `repository-governance` spec, the command reference and the changelog.
