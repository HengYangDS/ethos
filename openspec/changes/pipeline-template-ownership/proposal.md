# Proposal

## Why

ETHOS reads every YAML file under `.config/ci/` as a CI reference consumer
(`src/ethos/repository/policy/references/carriers.py`), but a Forge's runner declaration in
`.config/ci/runners.toml` owns an identity only in that Forge's own pipeline files
(`_pipeline_forge` in `src/ethos/repository/policy/references/closure.py`). A hosted template from
which a Forge's pipeline file is projected therefore belongs to no Forge, and an identity that both
the template and its projection use is refused as an orphan consumer even though the runner
declares it.

- On 2026-11-01 a replay of the unchanged alpha.20 and alpha.25 functions on di-effect's hosted
  templates refused eight identities, each of which has a runner declaration. The adopter cannot
  close the gap with its own declarations, and an allowlist would be a second owner of the same
  fact.
- The CI projection declaration, `.config/checks/ci-projection/policy.toml`, already names each
  copy projection's `template` and `projection`, and the paradigm already names each Forge's
  pipeline files, so a template's Forge follows from declarations that exist.

## What Changes

- A path that the CI projection declaration names as the template of a Forge's pipeline file
  belongs to that Forge for runner ownership. An identity such a template consumes is owned when
  the runner declaration of every Forge it projects into provides it.
- A YAML file under `.config/ci/` that no projection names stays unmapped, so an identity only a
  runner declaration provides is still an orphan consumer there.
- Patch admission and the repository semantic closure read the same mapping.
- Two corrections left by `declared-parameters`: the changelog gains its entry, and DR-0010 records
  the source-budget figures measured on the landed head.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: a runner declaration owns an identity in the declared templates of its
  Forge's pipeline files.

## Impact

`src/ethos/repository/policy/references/closure.py` and its tests, and the `repository-governance`
specification; `CHANGELOG.md` and `docs/decisions/dr-0010-source-budget-non-compensation.md` for
the two corrections. A governed repository whose hosted templates appear in its CI projection
declaration no longer has their runner identities refused; nothing else changes. A repository that
records its templates in a carrier of its own, as di-effect does in
`.config/tooling/repo/ci_template_consistency.toml`, gains this only after it declares them in the
CI projection declaration.
