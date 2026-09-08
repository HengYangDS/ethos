## REMOVED Requirements

### Requirement: Parity evidence is committed before Work Lane proof

**Reason**: A tracked evidence-record commit and directory-shape gate duplicate
the current Git-native Attestation and operation-specific exact-proof owner.
**Migration**: Select current proof by predicate and exact bindings in the
existing Attestation set; retrieve dated historical observations from Git.

## MODIFIED Requirements

### Requirement: Normative files remain distinct from directory roots

ETHOS SHALL retain safe repository-relative normative source declarations as
intent metadata independently from directory roots. Current proof SHALL be
selected by its Attestation predicate and exact bindings, independently from
documentation locations or historical evidence directories.

#### Scenario: Root-level normative source is declared

- **WHEN** an adopter declares `normative_sources = ["guidelines.md"]`
- **THEN** the typed current binding retains that exact safe source declaration
- **AND** directory roots keep their path-safety contract without creating a
  second evidence-root candidate selector.

## ADDED Requirements

### Requirement: Historical workspace evidence has no current proof role

ETHOS SHALL evaluate current proof through its existing selected Attestations
and exact operation bindings. The proof floor and repository documentation
audit SHALL operate independently of historical workspace evidence directories.
Git SHALL preserve removed committed records for historical retrieval.

#### Scenario: Historical directories are retired

- **WHEN** reviewed historical evidence and its duplicate documentation are
  removed from the current source tree
- **THEN** current proof consumers retain the same predicate and binding checks
- **AND** no directory-shape gate or required documentation placeholder remains.

#### Scenario: A new source file uses an old evidence path

- **WHEN** a maintained source file appears outside the official OpenSpec archive
- **THEN** its ordinary source class and budget apply
- **AND** an old evidence path supplies no automatic historical exclusion.
