## ADDED Requirements

### Requirement: A release tag publishes on its recorded qualification

For a release tag whose completed release effect created the exact tag object, publication SHALL admit the passing proof that effect embedded, verifying its identity, schema, subject, tree, artifact custody and recorded policy digest under the current runtime, without reading its set member or compiling the current policy for its source. Identity, signature, target policy and peer refs SHALL be checked now. Other targets keep the current policy.

#### Scenario: A later runtime changes the policy

- **WHEN** a peer misses or already holds a historical release tag after the policy changed
- **THEN** the missing peer receives the exact tag and the holding peer is recorded without a push
- **AND** the receipt binds the proof that the tag's release effect bound

#### Scenario: The bound proof cannot be verified

- **WHEN** the release record embeds no passing proof, its copy does not verify as the attestation it names, or its policy closure does not hash to its recorded digest
- **THEN** publication refuses by name before any peer changes

#### Scenario: A branch under a later policy

- **WHEN** a branch is published after the policy changed
- **THEN** its proof is still judged against the current policy
