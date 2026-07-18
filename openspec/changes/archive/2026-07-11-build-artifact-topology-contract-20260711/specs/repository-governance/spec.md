## MODIFIED Requirements

### Requirement: Generated Evidence Boundary
ETHOS SHALL keep generated proof artifacts outside repository truth while making
latest-artifact writes deterministic enough for proof gates. Its product package
build gate and contributor-facing package-build command SHALL route output to
`build/artifacts/python` and SHALL clear that local-artifact home before the
build; they SHALL NOT create a redundant output-local `.gitignore`, because the
repository-level ignore owns the generated home; and they SHALL NOT use the
repository-root `dist/` default.

#### Scenario: Shared coverage evidence writes are serialized

- **WHEN** the Python owner test gate writes generated coverage evidence
- **THEN** it serializes cleanup, shard combination, and latest XML writes for
  the shared coverage evidence directory
- **AND** the serialization mechanism does not create a new repository truth
  store
- **AND** local fallback evidence does not claim hosted CI success.

#### Scenario: Package build writes to the semantic artifact home

- **WHEN** the product full proof executes its package build gate or a
  contributor follows the documented package-build command
- **THEN** `uv build --all-packages --out-dir build/artifacts/python --clear
  --no-create-gitignore` is the invoked command
- **AND** generated package artifacts remain disposable local state under
  `build/artifacts/python`
- **AND** concurrent workspace package builds do not race on an output-local
  ignore marker
- **AND** the invocation does not create or authorize repository-root `dist/`
  output.
