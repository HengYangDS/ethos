## ADDED Requirements

### Requirement: Ownerless closeout lease observation is exact-subject scoped

ETHOS ownerless closeout SHALL validate the canonical lease schema and then
select lease rows using a bound equality predicate for the exact target
`subject` before strict row validation. Read-only ownerless state observation
and transactional closeout-fence acquisition SHALL use the same exact-subject
validator. Missing or valid expired exact rows SHALL be uncoordinated; a valid
unexpired exact row SHALL remain coordinated; malformed or ambiguous exact rows
SHALL remain fail-closed. Rows for any other subject SHALL NOT mint, suppress,
or block coordination for the target and SHALL NOT be rewritten by observation.

#### Scenario: unrelated legacy row does not block an exact target

- **GIVEN** the canonical lease schema is valid
- **AND** a legacy or malformed lease row belongs to a different subject
- **AND** the exact target has no current valid lease or Claim
- **WHEN** ETHOS observes the target or acquires its closeout fence
- **THEN** the unrelated row SHALL NOT make the target state unverifiable
- **AND** the query SHALL use complete subject equality rather than prefix,
  suffix, glob, or post-validation filtering
- **AND** no lease row SHALL be updated, deleted, migrated, or re-encoded.

#### Scenario: malformed exact target remains fail-closed

- **GIVEN** the canonical lease schema is valid
- **AND** the exact target row violates the current lease contract
- **WHEN** ETHOS observes the target or attempts closeout-fence acquisition
- **THEN** read observation SHALL report exact lease state as unverifiable
- **AND** fence acquisition SHALL conservatively block the ownerless effect
- **AND** the malformed exact row SHALL NOT be projected as absence.

#### Scenario: native admission and fenced re-observation share the boundary

- **GIVEN** a native ownerless decision and accepted Chronicle bind one exact
  target
- **AND** only unrelated historical lease rows fail the current row contract
- **WHEN** native admission observes the target, acquires its fence, and
  re-observes under that fence
- **THEN** all three stages SHALL admit the same exact-target lease facts
- **AND** any current or malformed exact-target row SHALL still stop the effect.

#### Scenario: invalid global schema stops exact observation

- **GIVEN** the shared lease table does not satisfy the canonical schema
- **WHEN** ETHOS evaluates any exact target
- **THEN** observation and mutation admission SHALL fail closed before treating
  the target as uncoordinated.
