## ADDED Requirements

### Requirement: A release tag publishes on its recorded qualification

For a release tag whose completed release effect created the exact tag object, publication SHALL admit the passing proof that effect bound, verifying its schema, subject, tree, artifact custody, embedded copy and recorded policy digest under the current runtime, without compiling the current policy for its source. Identity, signature, target policy and peer refs SHALL be checked now. Other targets keep the current policy.

#### Scenario: A later runtime changes the policy

- **WHEN** a peer misses or already holds a historical release tag after the policy changed
- **THEN** the missing peer receives the exact tag and the holding peer is recorded without a push
- **AND** the receipt binds the proof that the tag's release effect bound

#### Scenario: The bound proof cannot be verified

- **WHEN** the bound proof is missing from the set, differs from its embedded copy, or its policy closure does not hash to its recorded digest
- **THEN** publication refuses by name before any peer changes

#### Scenario: A branch under a later policy

- **WHEN** a branch is published after the policy changed
- **THEN** its proof is still judged against the current policy
