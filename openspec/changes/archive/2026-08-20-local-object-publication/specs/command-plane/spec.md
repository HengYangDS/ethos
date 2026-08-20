## ADDED Requirements

### Requirement: Publish is the sole remote Git object projection command

`ethos publish` SHALL be the sole public command that compiles, persists, and
applies remote Git object effects. It SHALL select typed targets from the
repository's positive ref topology, bind the exact local object and proof
Attestation, persist one content-addressed request, recheck every target before
the first effect, execute peer-local exact CAS, and emit one machine-readable
partial or complete Attestation. Tag publication and protected-branch
publication SHALL be modes of this command rather than separate commands or
hook exceptions.

#### Scenario: dry-run creates one immutable request

- **WHEN** a caller requests remote projection with exact local and peer facts
- **THEN** `ethos publish` SHALL return the request path, digest, source object, targets, proof, and exact apply command
- **AND** it SHALL perform no remote mutation

#### Scenario: apply consumes the same request

- **WHEN** request bytes and all bound coordinates remain current
- **THEN** `ethos publish --receipt ... --apply --authorize` SHALL execute only the request's effects
- **AND** it SHALL reject any repository, object, proof, ref, peer, or expected-OID drift

#### Scenario: missing proof is actionable

- **WHEN** the selected local object lacks the required exact proof Attestation
- **THEN** publish and pre-push SHALL report the same proof gap
- **AND** both SHALL identify `ethos prove --execute --expect-head <oid> --json` as the sole continuation

## REMOVED Requirements

### Requirement: Identity repair supports one receipt-bound linear suffix

**Reason**: Recreating a commit suffix under a different signature or identity
creates new product objects and contradicts the rule that publication transports
one locally created and signed object without replay or rewrite.

**Migration**: New objects must be correctly identified and signed before
creation. Existing divergent remote refs may be replaced only by an explicit
one-time exact expected-tip cutover to a selected existing local object; ETHOS
does not recreate commits or preserve a standing identity-repair command.
