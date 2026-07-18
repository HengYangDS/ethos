## MODIFIED Requirements
### Requirement: Generated Artifact Topology Gate

ETHOS SHALL keep generated artifact placement auditable so source, configuration,
semantic documentation, repository root, runtime state, generated proof output,
and curated evidence remain distinct authority surfaces.

#### Scenario: Root generated drift remains blocked while ignored test residue is local

- **WHEN** `ethos quality generated-artifacts --json` scans repository root paths
- **THEN** tracked or unignored generated outputs in repo root fail with
  `generated_artifact_repo_root_drift:<path>`
- **AND** ignored and untracked root `.coverage*`, `coverage.xml`, and `junit.xml`
  are reported as ignored local test residue rather than required gaps
- **AND** unrelated root generated outputs such as `proof.json` remain blocked
- **AND** the command remains read-only and does not clean files as part of the
  verdict
