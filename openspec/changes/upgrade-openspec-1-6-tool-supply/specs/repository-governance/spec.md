## ADDED Requirements

### Requirement: Deterministic Official OpenSpec Tool Supply

ETHOS SHALL invoke the official `@fission-ai/openspec@1.6.0` package from its
repository-owned npx fallback, CI bootstrap, and adopter scaffold surfaces,
while preserving explicit binary, cached official CLI, and PATH precedence.

#### Scenario: ETHOS-owned fallback and CI supply are inspected

- **WHEN** a maintainer inspects the OpenSpec adapter, CI bootstrap, and
  adopter CI scaffold
- **THEN** each repository-owned package invocation identifies
  `@fission-ai/openspec@1.6.0`
- **AND** strict official OpenSpec validation remains the governance gate
- **AND** an explicit `ETHOS_OPENSPEC_BIN`, cached official CLI, or PATH CLI
  retains its existing resolution precedence
