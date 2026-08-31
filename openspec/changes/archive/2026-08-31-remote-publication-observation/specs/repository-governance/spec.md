## ADDED Requirements

### Requirement: Remote publication observations preserve epistemic state

The existing remote-publication effect adapter SHALL be the sole owner of
bounded live remote-ref observation for exact publication. It SHALL preserve
whether a target ref is present, absent, or unavailable. Public CLI and Git
hooks SHALL consume that observation and SHALL NOT recreate availability,
ancestry, or object-identity judgments from missing coordinates.

#### Scenario: exact publication uses the target observer

- **WHEN** `ethos publish --ref <full-ref> --probe-remote` evaluates declared peers
- **THEN** the remote-effect adapter SHALL perform one bounded observation for
  each exact peer/ref target
- **AND** remote-tracking state or general reachability SHALL NOT substitute for
  that exact ref fact.

#### Scenario: a required remote fact is unavailable

- **WHEN** an exact target observation times out, cannot start, or exits without
  a valid ref result
- **THEN** publication SHALL return verdict `unknown` with the exact peer/ref
  missing fact, command boundary, cwd, exit or timeout state, and stderr
- **AND** it SHALL NOT report the ref as absent, divergent, or non-fast-forward.

#### Scenario: a divergent remote ref is observed

- **WHEN** a successful observation returns an existing OID that is neither the
  desired OID nor an admitted fast-forward predecessor
- **THEN** publication SHALL return verdict `block` with the observed OID and
  target-drift reason
- **AND** no remote mutation SHALL occur.

#### Scenario: apply re-observes the exact request

- **WHEN** a valid publication request is applied
- **THEN** every target SHALL be re-observed through the same bounded observer
  before the first effect and after its peer-local exact CAS
- **AND** unavailable post-observation SHALL not be reported as successful
  publication.
