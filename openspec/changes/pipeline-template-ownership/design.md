# Design

## Context

See [proposal.md](proposal.md). Two existing declarations meet here:

- The paradigm's `[[pipelines.forge]]` rows name each Forge's pipeline files
  (`.github/workflows/*.yml`, `*.yaml` for `github`, `.gitlab-ci.yml` for `gitlab`), and
  `_pipeline_forge` returns a path's Forge from them.
- `.config/checks/ci-projection/policy.toml` (schema `ethos-ci-template-consistency-v1`) declares
  projections; `projection_relations` (`src/ethos/repository/policy/projections.py`) returns each
  as a `Projection` whose `source` is the row's `template` and whose `output` is its `projection`.
  A `cue` row's source is the CUE model, which is not a reference carrier, so it never appears
  among consumer paths.

`_runner_provides` requires every consumer path of an identity to map to a Forge whose runner
declaration provides it, so one unmapped template refuses the identity. Patch admission
(`runner_provided_references`) and the repository semantic closure (`_orphan_consumers`) both call
it.

## Goals / Non-Goals

**Goals:**

- A declared template counts as a pipeline source of the Forges its projections reach, with the
  same runner rule as their pipeline files.
- An undeclared YAML file under `.config/ci/` keeps refusing a runner-only identity.

**Non-Goals:**

- Reading a repository's own template carrier. ETHOS reads its own declaration; di-effect's
  `.config/tooling/repo/ci_template_consistency.toml` moves to it in di-effect's migration.
- Projection consistency. Whether a projection equals its template stays with the CI projection
  check.

## Decisions

- **A consumer path's Forges.** A pipeline file has its own Forge. Any other path has the Forges of
  the pipeline files that a declared projection produces from it, and no Forge when none does. The
  mapping is derived from the two declarations, so no key is added. Rejected: a `forge` key on the
  projection row, which would restate what the output path already fixes; mapping every
  `.config/ci/` YAML file to every Forge, which would let one Forge's runner declaration cover
  another Forge's pipelines.
- **Every reached Forge provides.** A template projected into pipeline files of two Forges runs on
  both, so each Forge's runner declaration must provide the identity.
- **An invalid declaration maps nothing.** If `projection_relations` rejects the declaration, no
  template maps to a Forge and the closure stays refused; the CI projection check reports the
  declaration itself.
- **Admission reads the baseline.** Patch admission builds the mapping from the same baseline
  declaration files it reads `runners.toml` from, so a patch cannot admit its own template by
  editing the projection declaration in the same change.

## Risks / Trade-offs

- [The declaration is parsed once more per closure] → It is one small TOML file, parsed once per
  call.

## Migration Plan

One lane. Governed repositories need nothing; a repository that declares its hosted templates in
the CI projection declaration stops seeing their runner identities refused.
