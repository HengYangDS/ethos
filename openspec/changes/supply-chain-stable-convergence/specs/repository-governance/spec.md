## MODIFIED Requirements

### Requirement: Deterministic Official OpenSpec Tool Supply

ETHOS SHALL invoke the repository-locked official `@fission-ai/openspec@1.12.0`
package from its declared local runtime and CI bootstrap. The effective package
identity SHALL derive from the repository package declaration and lockfile;
ambient npx, PATH, cache, and global versions SHALL not be accepted as a
fallback. Adoption SHALL NOT generate an OpenSpec workspace or provider CI
surface.

#### Scenario: ETHOS-owned fallback and CI supply are inspected

- **WHEN** a maintainer inspects the OpenSpec adapter and CI bootstrap
- **THEN** each repository-owned package invocation SHALL resolve the locked
  `@fission-ai/openspec@1.12.0` identity
- **AND** strict official OpenSpec validation SHALL remain the governance gate
- **AND** adoption SHALL plan no OpenSpec or CI carrier.
