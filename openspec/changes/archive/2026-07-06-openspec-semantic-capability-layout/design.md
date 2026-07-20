## Context

The official OpenSpec boundary is the current capability workspace under
`openspec/specs`. The ETHOS product boundary is kernel-first: capability IDs
must describe stable semantic responsibilities, while implementation homes stay
metadata.

## Design

Use one flat OpenSpec capability directory per primary invariant:

- `kernel`
- `contracts`
- `repository-governance`
- `adapters`
- `command-plane`
- `assistant-projections`
- `distribution`
- `quality`
- `proof-hosts`

This keeps OpenSpec compatible with the official `specs/<capability>/spec.md`
carrier shape while removing the retired package-shaped identity layer. The
profile `owner.package` records the current physical owner (`ethos-core` or
`ethos`) without becoming the capability ID.

## Alternatives

- Keep `ethos-*` IDs: rejected because they preserve a stale package ontology and
  make current design look older than implementation truth.
- Add nested family directories: rejected because it would fight OpenSpec's
  simple capability lookup and create an extra entity.
- Collapse all surfaces into one capability: rejected because command, assistant,
  and distribution surfaces have different boundaries and proof questions.

## Proof Strategy

- Official `openspec validate --all --strict --json` must pass.
- `ethos openspec --lifecycle --json` must report no lifecycle gaps.
- Repository audit must require the semantic capability set.
- Adoption scaffold tests must prove new repositories receive the semantic set.
- Architecture tests must prove active change deltas use the semantic capability
  IDs.

## Quality Gate Absorption

Absorb reference-repository mechanisms by invariant rather than by tool center:

- `.config/checks/` owns reusable policy only; runtime outputs go to
  `build/evidence/quality/` or `build/runtime/`.
- `.config/ci/scripts/` owns executable gates; GitLab and pre-commit only invoke
  those scripts.
- The Python test gate is parallel-capable, timeout-bound, duration-visible, and
  writes JUnit/coverage artifacts under `build/evidence/quality/tests/`.
- The docstring gate admits Google style, rejects legacy structured sections,
  validates structured `Args` sections against signatures, and exposes a
  non-blocking broader public-definition inventory for future tightening.
- Repository hygiene absorbs the useful pre-commit-hooks class of checks without
  making pre-commit the truth center.

Rejected mechanisms for this change: introducing pixi, nox, tox, Docker-gate,
Allure, or benchmark gates as active centers. They remain unnecessary entities
until a concrete ETHOS proof profile needs them.
