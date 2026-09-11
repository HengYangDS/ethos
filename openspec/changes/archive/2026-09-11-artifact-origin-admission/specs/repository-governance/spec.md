## ADDED Requirements

### Requirement: Executable topology policy shares runtime identity

The executable topology declaration SHALL be a native resource of the package
that interprets it. Working-directory and audited-repository files SHALL NOT
replace that runtime policy. Missing or malformed package policy SHALL fail
closed. Successor code and declaration SHALL be validated together while the
installed predecessor continues governing the transition with its own policy.

#### Scenario: Candidate declaration evolves

- **WHEN** the successor changes its topology schema and removes the old carrier
- **THEN** the predecessor continues loading its own package policy
- **AND** the successor loads its own declaration without a compatibility copy
- **AND** normal hooks, intent and fresh mutation admission remain required

#### Scenario: Audited checkout offers an incompatible override

- **WHEN** an unrelated checkout supplies an incompatible topology declaration
- **THEN** public artifact observation still uses the executing package policy
- **AND** it does not parse that checkout declaration as its executable policy

### Requirement: Artifact origin is independent of presentation

Artifact admission SHALL derive generation ownership from native producer
declarations or lifecycle ownership, not filename suffix, format ownership,
tracking or existence alone. Without that evidence it SHALL retain unclassified
origin and apply ordinary source admission independently of placement rules.

#### Scenario: Authored native configuration

- **WHEN** an owned lane requests a native configuration with no generated owner
- **THEN** its serialization format does not create a generated-artifact rejection
- **AND** ordinary intent, containment and authority checks remain required

#### Scenario: Missing path

- **WHEN** a requested path does not exist
- **THEN** admission reports absence separately from ownership
- **AND** absence does not prove generation, successful deletion or consumer closure

### Requirement: Native generated projections retain one producer

Generated projection admission SHALL use the declared source/output relation and
the native producer's verification semantics. It SHALL distinguish source inputs
from generated outputs and reject an unverifiable or conflicting owner rather
than silently admit a manual output edit.

#### Scenario: Generated output edit

- **WHEN** an exact patch changes a declared output inconsistently with its source
- **THEN** admission blocks with the producer and output identified
- **AND** an output matching the same patch's source passes that projection check

#### Scenario: Source model is authored

- **WHEN** a projection input and output share a formatter or file family
- **THEN** only the declared output is classified as producer-owned
- **AND** formatter assignment creates no generation authority

#### Scenario: Projection ownership is retired

- **WHEN** an exact patch removes an output and its producer relation coherently
- **THEN** admission evaluates surviving consumers and permits a closed retirement
- **AND** removing only the declaration cannot silently authorize arbitrary output bytes

#### Scenario: Git commit evaluates its prospective index

- **WHEN** the Git pre-commit transport checks a generated projection
- **THEN** it obtains producer and output bytes from the exact staged tree
- **AND** unstaged source or output changes cannot alter that verdict
- **AND** it consumes the same producer and deletion semantics as patch admission
- **AND** changed HEAD or index coordinates invalidate the in-flight observation

### Requirement: Deletion admission preserves affected consumers

Exact patch admission SHALL retain deleted paths and evaluate affected surviving
native consumers against the effective postimage. It SHALL permit removal with
consumer updates, reject a surviving required input and preserve unknown coverage
when the required native relationship cannot be resolved.

#### Scenario: Authored configuration and consumer retire together

- **WHEN** a patch removes configuration and updates its explicit native consumer
- **THEN** no generation exception is needed and the closed deletion is admitted
- **AND** preimages, caller ownership and exact paths remain checked

#### Scenario: Required native consumer survives

- **WHEN** a patch removes a file still selected as an explicit native input
- **THEN** admission blocks and names the deleted input and surviving consumer
- **AND** unchanged consumers are not omitted because they have no patch entry

### Requirement: Artifact admission failures identify a usable continuation

Public artifact admission SHALL distinguish ownership, existence, placement and
proposed effect. A failure SHALL expose the relevant boundary and one next
observation or exact patch command; it SHALL NOT suggest replaying an unchanged
request as a repair.

#### Scenario: Producer output lacks an exact proposed effect

- **WHEN** output admission requires verification but no patch is supplied
- **THEN** the result requests an exact patch with current root and paths
- **AND** it does not claim any mutation occurred

#### Scenario: Invalid working declaration is repaired

- **WHEN** a producer declaration has invalid uncommitted syntax
- **THEN** public admission identifies an exact repair-patch continuation
- **AND** it permits a valid postimage only after retaining known baseline owners
- **AND** unrelated changes cannot use invalid ownership as permission
