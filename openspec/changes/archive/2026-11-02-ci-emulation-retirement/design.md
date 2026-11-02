# Design

## Context

See [proposal.md](proposal.md). `tools/ci/ci_templates.py` holds two commands: `check-templates`,
which compiles the CUE model and compares both projections (the `ci_templates` gate calls its
`check_templates`, and `.config/checks/format-selection/policy.toml` renders through
`check-templates --render`), and `emulator-evidence`, which runs `act` or `gitlab-ci-local` on a
snapshot that `tools/ci/provider_materialization.py` builds. `tools/ci/ci_projection.py` validates
the emulator fields of every `[[projection]]` entry and copies them into the template evidence.

## Goals / Non-Goals

**Goals:**

- No local CI emulation remains in ETHOS's tooling, configuration, tests or documents.
- `check-templates` and the `ci_templates` gate keep their behavior.

**Non-Goals:**

- Package topology. `src/ethos/contracts/artifacts/topology.toml` and
  `src/ethos/repository/policy/artifact_entrypoints.py` keep their rules for repositories that run
  `gitlab-ci-local` themselves.
- Reference declarations. `src/ethos/repository/policy/references/declarations.py` keeps owning
  an `emulator_tool` or `emulator_image` that a repository declares.
- The local CI fallback (`nox -s local_ci`), which runs the full gate closure, not an emulator.

## Decisions

- **Keep `check-templates` where it is.** Its callers name `tools/ci/ci_templates.py`; moving it
  would change the format-selection policy and the reference carriers for no gain.
- **Keep one GitLab image assertion.** The projection test compared the GitLab jobs' image with the
  emulator's declared image; it now requires that every GitLab job uses one digest-bound image.
- **Modify, not add.** The three spec passages are edited in place. OpenSpec refuses a modified
  requirement that drops a scenario, so "Local provider emulation remains local evidence" keeps
  its name and now states that a hand-run emulator's output is never read as evidence; the two
  quality requirements drop the emulation plane.

## Risks / Trade-offs

- [A contributor wants to rehearse a workflow locally] → They can still run `act` or
  `gitlab-ci-local` by hand on the projected files; ETHOS no longer records that run as evidence.
