## MODIFIED Requirements

### Requirement: Documentation Quality Profile

ETHOS SHALL make documentation faithfulness, expressiveness, and elegance
mechanically checkable through metadata, visible reader sections, glossary,
links, anchors, and command examples.

#### Scenario: Docs profile is reported

- **WHEN** `ethos quality docs --json` runs
- **THEN** ETHOS reports docs quality profile checks alongside governed docs
  registry health

#### Scenario: Tracked Markdown violates its native lint policy

- **WHEN** `tools/ci/scripts/run-markdown-lint.sh` evaluates tracked Markdown
  that violates the configured markdownlint policy
- **THEN** the owner script fails with a line-addressed diagnostic
- **AND** hosted CI does not report the quality workflow or repository proof as
  successful
- **AND** the gate does not rewrite the governed document automatically
