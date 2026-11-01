## ADDED Requirements

### Requirement: Generated artifacts stay outside repository truth

Generated proof artifacts SHALL remain outside repository truth, with deterministic latest-artifact
writes. Product and contributor package builds SHALL build in a disposable staging directory and
replace `build/artifacts/python`, or `build/artifacts/release/python` for a release build, with
exactly one admitted wheel; they SHALL rely on the repository-level ignore and SHALL NOT use root
`dist/` or add an output-local `.gitignore`.

#### Scenario: Package build writes to the semantic artifact home

- **WHEN** the product full proof executes its package build gate or a contributor follows the
  documented package-build command
- **THEN** the `build` owner runs `uv build` with `--out-dir <staging>` and `--no-create-gitignore`,
  then replaces `build/artifacts/python` with the one admitted wheel
- **AND** generated package artifacts remain disposable local state under `build/artifacts/python`
- **AND** concurrent workspace package builds do not race on an output-local ignore marker
- **AND** the invocation does not create or authorize repository-root `dist/` output.

## REMOVED Requirements

### Requirement: Generated Evidence Boundary

**Reason**: Two of its three scenarios described the shared coverage evidence home and its writer
lock, which belonged to the retired `tools/ci` test gate. The probe keeps each attempt's coverage in
that attempt's scratch, so no shared writer remains to serialize. A MODIFIED block cannot drop
scenarios, so the requirement's statement and its package-build scenario move unchanged to
"Generated artifacts stay outside repository truth".

**Migration**: Read "Generated artifacts stay outside repository truth" for the package-build rule;
`ETHOS_COVERAGE_LOCK_WAIT_SECONDS` has no effect.

### Requirement: Python test basetemp has one explicit owner

**Reason**: The probe allocates pytest's basetemp inside its own scratch root and removes it with
the attempt. No caller-supplied basetemp input remains; `ETHOS_TEST_BASETEMP` retires with the
runner that read it.

**Migration**: A direct pytest run that needs a fixed temporary root passes pytest's native
`--basetemp`. Proofs need none.
