## ADDED Requirements

### Requirement: Exact commit proof binds observed execution source

An exact-commit proof SHALL bind matching working content and index to its commit
before execution and revalidate their correspondence after execution, at issuance
and at selection of the new result. Missing or changed inputs SHALL prevent a
passing exact-commit result without altering the user's source or index.

#### Scenario: Source or index changes during a successful gate

- **WHEN** a gate returns success but tracked source, policy, index or non-ignored inputs differ from the bound commit
- **THEN** exact-commit proof is refused and the source mismatch remains observable
- **AND** no passing new Attestation is selected and no source content is restored or discarded

#### Scenario: Exact execution begins with dirty source

- **WHEN** a request would execute exact-commit proof over a different checkout or index
- **THEN** source admission refuses before executing the gates
- **AND** exploratory host observations remain distinct from repository proof

#### Scenario: Clean source produces ignored output

- **WHEN** the gates leave the bound source and index unchanged while writing ignored diagnostic output
- **THEN** source admission permits the otherwise valid proof

#### Scenario: Historical evidence lacks execution binding

- **WHEN** a proof lacks the required source correspondence in its carried plan
- **THEN** it cannot satisfy the new exact-source proof contract
- **AND** its historical record remains unchanged

#### Scenario: Adversarial isolation is required

- **WHEN** an authority requires protection from hostile writers between source observations
- **THEN** sampled source equality alone does not establish that stronger guarantee
