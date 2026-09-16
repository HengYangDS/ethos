## ADDED Requirements

### Requirement: Gate representation preserves common governance

ETHOS SHALL evaluate applicable binding, OpenSpec, commit and declared release
obligations independently of inline or registry gate storage. Product-specific
conformance SHALL use explicit provider composition while retaining the trusted
predecessor verification floor during control replacement.

#### Scenario: Equivalent adopter gate declarations

- **WHEN** two otherwise equivalent adopters store the same gates inline or in a registry
- **THEN** common governance and relevant effect admission yield equivalent outcomes
- **AND** neither requires ETHOS product documents or package metadata by implication.

#### Scenario: Real OpenSpec observation fails

- **WHEN** an enabled adopter OpenSpec configuration is invalid
- **THEN** public audit reports the actual required gap
- **AND** no capability boolean replaces that observation with a passing result.

#### Scenario: Candidate removes predecessor product verification

- **WHEN** a candidate disables a verification obligation required by its accepted predecessor
- **THEN** its control-replacement acceptance still requires the predecessor obligation
- **AND** candidate gate storage or profile naming cannot waive it.

### Requirement: Declared release roles share one validation owner

ETHOS SHALL validate present release-role declarations against configured branch
roles through one semantic owner. Missing optional declarations impose no release
constraint. Malformed present declarations fail closed. Branch membership is
order-independent; duplicate or incorrectly typed entries are invalid.

#### Scenario: Contradictory protected branch declarations

- **WHEN** declared protected branches omit or add a branch relative to effective protected roles
- **THEN** common audit and relevant integration admission reject with a precise policy gap
- **AND** the attempted integration leaves its destination ref unchanged.

#### Scenario: Equivalent branch order

- **WHEN** a declaration contains each effective protected branch exactly once in a different order
- **THEN** its role-consistency check passes.

#### Scenario: Absent optional release declaration

- **WHEN** an adopter does not declare release configuration
- **THEN** common governance imposes no product release files, tag convention or attestation format.

#### Scenario: Malformed present declaration

- **WHEN** present release configuration is unreadable, malformed or has invalid protected-ref fields
- **THEN** the owning report identifies the invalid declaration
- **AND** no consumer silently converts it to absent policy.

### Requirement: Runtime binding reports selected schema provenance

ETHOS SHALL derive schema provenance from the actual runner schema owner and
runtime admission from the selected execution authority. Correctly bound package
execution SHALL NOT require schemas in the adopter checkout. Profile validity or
gate representation alone SHALL NOT grant mutation authority.

#### Scenario: Registry adopter uses its selected package runtime

- **WHEN** a registry adopter invokes its current immutable package runtime
- **THEN** prewrite admits a valid otherwise-authorized write
- **AND** diagnostics identify the package schema origin without claiming local schemas.

#### Scenario: Unrelated adopter schema path

- **WHEN** an adopter contains a file whose name resembles an ETHOS schema
- **THEN** that file does not change the reported or selected runner schema source.

#### Scenario: Stale execution authority

- **WHEN** a tracked mutation invokes a stale or foreign execution authority
- **THEN** admission rejects under the existing currentness boundary
- **AND** supplies recovery derived from the current target and selected runtime.
