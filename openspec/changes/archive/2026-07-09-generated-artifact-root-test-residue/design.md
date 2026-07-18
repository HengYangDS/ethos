# Design

## Boundary

This change narrows one false-positive path in the generated-artifact topology
gate. The repository root remains denied for generated output. The only tolerated
paths are ignored, untracked local coverage/pytest residue names already owned by
the Python test gate cleanup boundary.

## Mechanism

`generated_artifact_topology_report()` still walks candidate generated-artifact
paths and applies the contract. Before classifying a root test-residue filename,
it asks Git whether that path is ignored and not tracked. Only that combination
is reported under `ignored_local_paths` and skipped as local cleanup debt.
Tracked residue and unrelated root generated outputs continue through the normal
policy and fail with `generated_artifact_repo_root_drift:<path>`.

The core topology contract recognizes `.coverage.*` filenames as generated so
tracked coverage shard residue is still visible to the gate.

## Alternatives

- Move cleanup into `ethos prove`: rejected because standalone `ethos quality
  generated-artifacts --json` would still disagree with proof.
- Depend `generated-artifacts` on `unit-architecture`: rejected because it makes
  topology correctness depend on a slower test gate and hides standalone drift.
- Ignore all root generated files: rejected because it weakens the gate and
  allows proof/report output to become root clutter.

## Proof Strategy

- Red tests for ignored local test residue and tracked root residue.
- Real command reproduction with `.coverage`, `.coverage.worker`, `coverage.xml`,
  and `junit.xml` present at repo root.
- Negative command reproduction that `proof.json` still fails as root drift.
- Focused generated-artifact topology, CLI, docs, testing-platform, lint, types,
  OpenSpec lifecycle, claims, evidence freshness, and HEAD-bound proof checks.
