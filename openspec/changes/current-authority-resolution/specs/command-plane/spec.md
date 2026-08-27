## ADDED Requirements

### Requirement: Current Work Lane authority has one fresh resolver

ETHOS SHALL resolve current tracked-write authority from the current branch/ref
HEAD and tree, invocation actor, exact Lease generation, and the exact
Lease-bound Commitment. Historical transition Attestations SHALL NOT mint,
revoke, or replace that current authority.

#### Scenario: Current binding is exact without historical transition evidence

- **GIVEN** the invocation actor owns a valid Lease whose ID, epoch, expected
  HEAD/tree, carrier bytes, and Commitment digest match the current Work Lane
- **AND** the requested paths are covered by that Commitment
- **WHEN** historical start, rebind, or archive effect Attestations are absent
- **THEN** status, plan, prewrite, and pre-commit project the same passing
  current-authority coordinates
- **AND** no surface reports change_generation_authority_missing.

#### Scenario: Current binding is stale or ambiguous

- **WHEN** any required actor, Lease generation, HEAD/tree, carrier bytes, or
  Commitment digest coordinate is missing or mismatched
- **THEN** every consuming surface fails closed with the same first exact reason
- **AND** historical transition evidence cannot override the mismatch.

#### Scenario: Historical transition evidence remains provenance

- **WHEN** valid transition Attestations are available
- **THEN** generation path attribution and effect verification may cite them
- **AND** removing them changes provenance detail only, not a valid current
  authoring verdict.
