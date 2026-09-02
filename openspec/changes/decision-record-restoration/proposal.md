## Why

Deleting the former decision-record subsystem correctly removed indexes,
templates, lifecycle folders, and executable decision machinery, but it also
removed several design choices whose alternatives and revisit conditions are
not carried by current product contracts. At the same time, `docs/index.md`
duplicates `docs/README.md` as a documentation entrypoint.

## What Changes

- Make `docs/README.md` the sole current documentation entrypoint and delete
  `docs/index.md` plus its active references and stable-path declaration.
- Restore only three still-distinct design rationales under `docs/decisions/`,
  using lowercase semantic filenames.
- Merge the former documentation-topology records into one portability
  decision and do not restore the retired proof-scope compatibility record.
- Keep current semantics in their existing product, source, policy, and
  configuration owners; decision records explain why and authorize nothing.
- Do not add a decisions README, index, template, schema, registry, validator,
  lifecycle directory, or runtime consumer.
- Preserve immutable historical evidence and archived OpenSpec bytes even when
  they mention retired paths.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: expose one documentation entrypoint and retain only
  irreducible decision rationale without recreating a parallel authority.

## Impact

Current documentation navigation, repository path classification, Markdown
reference policy, and three documentation-only decision records are affected.
Runtime transitions, Commitment, Lease, Attestation, and adopter layouts are
unchanged.
