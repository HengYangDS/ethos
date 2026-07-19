## Context

The recovered lanes all describe the same product gap, but their implementation
predates the current two-package topology, declaration-resource packaging, and
source-budget programme.  The current replay must preserve the semantic
boundary while removing historical branch topology from the implementation.

## Design

The profile remains the sole opt-in entrypoint.  If `.ethos/profile.toml` is
absent or does not contain `[container_contract]`, schema validation reports an
advisory `not_declared` state and does not invent a deployment requirement.
When it is present, the validator:

1. validates the short profile declaration with the product declaration schema;
2. resolves the manifest only below the governed repository root;
3. validates the manifest with the product contract schema;
4. checks semantic facts that JSON Schema alone cannot prove: exact Linux
   architecture smoke coverage, unique asset identifiers, persistent restore
   policy, evidence hash/tracking, untrusted output schema validity, and the
   provider-neutral naming boundary;
5. contributes failures to `schema_validation_report`, so a declared invalid
   contract blocks normal promotion through the existing proof surface.

The implementation is a thin adapter over product schemas and Git evidence.
It does not add a public command, a second lifecycle, or a runtime-specific
execution engine.  Tests use a miniature adopter repository and mutate one
contract fact at a time.

## Alternatives

- **Archive all recovered lanes without replay:** rejected because the accepted
  product lacks the documented opt-in validation capability.
- **Merge the recovery branch:** rejected because it imports obsolete packaging
  and accumulated source-budget structure rather than current contracts.
- **Accept any adopter-local schema:** rejected because a relaxed local copy
  could make an invalid contract appear valid.

## Verification

- A red-green parametrized fixture suite covers absent, valid, malformed,
  escaped, vendor-branded, untracked, stale, incomplete, and duplicate cases.
- Schema-report integration proves that declared invalid contracts become
  promotion-relevant while undeclared repositories remain valid.
- Strict OpenSpec, changed-scope planning, parity, executed proof, candidate
  land, accepted-root closeout, and native source-lane resolution remain
  separate later lifecycle effects.
