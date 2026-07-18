# Generated Artifact Root Test Residue

## Why

`ethos quality generated-artifacts --json` should detect real root generated
artifact drift, but it should not depend on whether the Python test owner script
has already cleaned ignored local coverage or pytest residue. A stale local
`.coverage` file could make the generated-artifacts gate fail before the
unit-architecture gate ran and removed the same ignored residue.

## What Changes

- Keep root generated artifact drift denied by default.
- Treat only ignored and untracked root `.coverage*`, `coverage.xml`, and
  `junit.xml` as local test residue rather than repository truth.
- Keep tracked copies of those files blocked as root generated drift.
- Record the tolerated residue in the generated-artifacts payload so the verdict
  remains explainable.
- Align `.gitignore`, docs, decision record, and regression tests with the test
  owner script cleanup boundary.

## Capabilities

- `quality`: subject=generated-artifact-root-test-residue; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=quality,docs,openspec,test;
  facet:authority=source,test,docs,openspec,claim,evidence

## Out Of Scope

- No root output home is added.
- No broad ignore of generated files is introduced.
- No tracked root generated artifact is allowed.
- No hosted CI or remote publication is claimed.
