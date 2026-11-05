## ADDED Requirements

### Requirement: A repaired release tag is re-created on its replacement commit

ETHOS SHALL re-create a release tag whose target a completed signature repair replaced as a signed annotated tag on the mapped commit, keeping the original name, tagger, date and message, and SHALL record one attestation binding both tag objects, the mapping attestation and the mapped target. An unmapped target, a missing original, an occupied name or an untrusted signer SHALL refuse by name.

#### Scenario: A repaired tag is re-created

- **WHEN** a release tag targets a commit that a completed repair mapped to a replacement
- **THEN** the re-created tag targets the replacement with the original header and message
- **AND** one attestation binds the old and new tag objects, the mapping attestation and the target

#### Scenario: A batch holds an unmapped tag

- **WHEN** a re-tag batch names a tag whose target no completed repair mapped
- **THEN** that tag refuses by name and no ref moves

### Requirement: A re-created release tag publishes on its original qualification

Publication SHALL qualify a re-created release tag by the proof that its original tag's release record embeds, admitted as recorded on the original commit, only when one re-tag receipt binds the exact tag object and its mapping still verifies; the original proof's set member SHALL NOT be required. A re-created tag without a receipt SHALL keep the current policy.

#### Scenario: A re-created tag under a later policy

- **WHEN** a re-created tag is published after the policy changed and the original proof's set member has ended
- **THEN** publication admits the original release record's proof and the peer receives the re-created tag

#### Scenario: A re-created tag without its receipt

- **WHEN** no re-tag receipt binds the re-created tag object
- **THEN** its publication is judged under the current policy, and without a current proof it refuses before any peer changes
