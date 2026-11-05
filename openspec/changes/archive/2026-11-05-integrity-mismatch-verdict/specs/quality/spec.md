## ADDED Requirements

### Requirement: Source integrity separates conflicts from unverifiable members

The integrity provider SHALL report a member whose bytes differ from what its native owner renders or from its pinned original as `block`, with `source_generated_bytes_mismatch:<path>`, `source_upstream_member_mismatch:<path>` or `source_upstream_archive_digest_mismatch:<path>`. A member it cannot read, qualify or compare SHALL stay `unknown` with `source_integrity_unproven:<path>`.

#### Scenario: A generated artifact drifts

- **WHEN** a generated artifact's bytes differ from what its declared native owner renders
- **THEN** the integrity gate reports `block` with `source_generated_bytes_mismatch:<path>`

#### Scenario: A member cannot be compared

- **WHEN** a declared member or its archive cannot be read or qualified
- **THEN** the integrity gate reports `unknown` with `source_integrity_unproven:<path>`
