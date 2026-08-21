## ADDED Requirements

### Requirement: Hook runtime currentness is mutation admission
ETHOS SHALL distinguish runtime byte integrity from accepted-source currentness.
A hook runtime SHALL authorize repository mutation only when its manifest is
valid and its source commit and tree equal the exact expected ETHOS identity.

#### Scenario: intact runtime was built from older accepted source
- **WHEN** every recorded runtime byte is intact but its source commit or tree differs from the expected accepted identity
- **THEN** runtime observation reports a stable stale-source required gap
- **AND** prewrite, hook, ref effect, and lifecycle mutation paths fail closed

#### Scenario: accepted runtime is current
- **WHEN** runtime bytes, launchers, source commit, and source tree all match their expected identities
- **THEN** the existing hook runtime binding reports no required gap
- **AND** no separate current-generation pointer or mutable runtime registry is consulted

#### Scenario: repair replaces the stale projection
- **WHEN** the exact public repair command succeeds
- **THEN** the command atomically activates launchers for a runtime built from the expected identity
- **AND** post-observation proves both byte integrity and source currentness before reporting success
