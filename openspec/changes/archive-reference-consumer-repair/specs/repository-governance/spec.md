## ADDED Requirements

### Requirement: Attested archive admits bounded authored reference repair

After an official archive, ETHOS SHALL derive repair scope for a tracked Markdown
document only when its parsed local destination still names an artifact moved by
that exact attested archive. The current Git tree, runtime, actor, Lease and
postimage admission remain required. Repair SHALL NOT replay archive, silently
rewrite authored prose or create another tracked intent authority.

#### Scenario: A current document retains a navigable active-Change link

- **GIVEN** an exact archive effect is attested and its archived target exists
- **AND** a tracked authored Markdown document still links to the removed active artifact
- **WHEN** its owner requests exact-path prewrite or stages a reviewed repair
- **THEN** prewrite and the native commit hook admit only that document
- **AND** ordinary patch, source freshness and repository quality checks still apply
- **AND** the repair scope disappears when the stale link leaves the committed tree

#### Scenario: A mention does not establish a repair relation

- **WHEN** the requested file contains only code-fenced text, an unrelated path or no parsed link to the moved artifact
- **THEN** the archive grants no write scope to that file
- **AND** a missing target, unsupported reference or absent archive Attestation remains blocked
