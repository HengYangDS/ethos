## MODIFIED Requirements

### Requirement: Local-ci fallback projects owner scripts from target root

ETHOS local-ci fallback evidence SHALL derive invoked owner scripts from the
actual target repository's local-ci script and SHALL expose whether local fallback
evidence is bound to the current Git HEAD.

#### Scenario: local-ci fallback evidence is stale, missing, invalid, or current

- **WHEN** `ethos publish --json` assembles local-ci fallback evidence
- **THEN** the fallback package reports `evidence_status.path`,
  `evidence_status.current_head`, `evidence_status.evidence_head`,
  `evidence_status.state`, and `evidence_status.ok`
- **AND** stale, missing, or invalid local-ci fallback evidence directs the caller
  to rerun `tools/ci/scripts/run-local-ci.sh`
- **AND** current fallback evidence says only that local CI fallback evidence is
  current at HEAD; it does not claim hosted CI success or remote publication
