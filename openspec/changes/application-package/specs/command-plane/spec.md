## ADDED Requirements

### Requirement: The application package owns every shared operation

The status, planning, adoption, proof, integration and publication operations SHALL live in
`ethos.application` and return typed results without rendering them. The surfaces and `ethos.cli`
SHALL NOT add imports of `domain`, `adapters`, `repository`, `normalization` or `assistants`, and
`domain` SHALL NOT add imports of `adapters`; the import contracts list the remaining edges.

#### Scenario: Proof is reached as an application operation

- **WHEN** a caller invokes `prove_repository` with a repository and a proof request
- **THEN** its verdict, state, gaps and continuation equal those that `ethos prove --json` reports
  for the same request
- **AND** the call writes no stdout and raises no `SystemExit`

#### Scenario: A surface adds an import of a lower layer

- **WHEN** a surface module imports `ethos.adapters`, `ethos.domain` or `ethos.repository` along an
  edge that the import contracts do not list
- **THEN** the import-boundaries gate fails

#### Scenario: A listed import is removed

- **WHEN** an edge that the import contracts list no longer exists
- **THEN** the import-boundaries gate fails until the list drops it
