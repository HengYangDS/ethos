## ADDED Requirements

### Requirement: Topic-scoped Chronicle Evidence Layout

ETHOS SHALL keep judged human-readable proof records under topic-scoped
chronicle directories instead of loose evidence-root Markdown or flat chronicle
Markdown.

#### Scenario: evidence root stays shallow

- **WHEN** dated proof Markdown is promoted into tracked evidence
- **THEN** it is stored as `evidence/chronicle/<topic>/<date>.md`
- **AND** `evidence/` root contains only `README.md` and semantic owner
  directories
- **AND** `evidence/chronicle/` contains topic directories, not loose Markdown
  files.

#### Scenario: claim digests survive relocation

- **WHEN** a claim points at a topic-scoped chronicle record
- **THEN** the claim quality gate verifies the referenced file digest
- **AND** moving the path does not weaken the digest binding to the evidence
  content.
