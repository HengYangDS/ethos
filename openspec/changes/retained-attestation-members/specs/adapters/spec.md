## MODIFIED Requirements

### Requirement: Attestation evidence bytes use released local custody

ETHOS SHALL store evidence bytes outside the Attestation set, in a content-addressed store in the
Git common directory that is never tracked or published. A member SHALL bind each stored file as
`custody:sha256:<digest>` in its evidence references. Stored bytes SHALL be deleted once no selected
member binds their digest.

#### Scenario: Evidence is recorded

- **WHEN** a record declares `custody:sha256:<digest>` and supplies a file with exactly that digest
- **THEN** the file is stored byte-exact under its digest and the member is added
- **AND** the worktree index, tracked files and remotes are unchanged

#### Scenario: Declared evidence is missing or differs

- **WHEN** a declared custody digest has neither stored bytes nor a supplied file with that digest
- **THEN** the record fails closed before any effect

#### Scenario: Evidence is released

- **WHEN** the last selected member that binds a custody digest leaves the set
- **THEN** the stored bytes for that digest are deleted
- **AND** bytes still bound by another member remain

#### Scenario: A record races the deletion of its evidence

- **WHEN** a record binds bytes that a concurrent update is deleting
- **THEN** the record waits for the deletion and stores its bytes again
- **AND** a cleanup failure after a swap is reported without failing the update

#### Scenario: A failed cleanup left unbound bytes

- **WHEN** a cleanup failure after a swap left bytes that no selected member binds
- **THEN** the next set update that holds the custody lock deletes them
- **AND** no caller action is needed to recover from the reported gap

#### Scenario: An update fails after storing evidence

- **WHEN** an update stores custody bytes and then exhausts its exact-CAS retries
- **THEN** the stored bytes that no selected member binds are deleted
- **AND** the update still fails with `attestation_set_cas_retry_exhausted`
