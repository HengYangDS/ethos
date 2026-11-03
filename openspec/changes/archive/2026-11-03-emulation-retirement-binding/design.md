# Design

## Context

See [proposal.md](proposal.md). Reference closure owns an identity when a declaration owns it in
every file, or when the runner of every Forge that a consuming pipeline file runs on provides it
(`_runner_provides` in `src/ethos/repository/policy/references/closure.py`). The emulator
declaration was the first kind of owner; `.config/ci/runners.toml` is the second.

## Goals / Non-Goals

**Goals:**

- Reference closure finds no orphan consumer at the landed head, and GitLab accepts the supply
  manifest of the landed head.

**Non-Goals:**

- Owning Docker in every file. Only the pipeline files of a Forge whose runner provides it may use
  it.
- Removing the product's reading of an `emulator_tool` or `emulator_image` that another repository
  declares; `ci-emulation-retirement` kept it.
- Changing any supply version.

## Decisions

- **Declare Docker per Forge in the runner record.** The GitHub-hosted Ubuntu image ships Docker
  with Buildx, and ETHOS's GitLab runners use the Docker executor, so each runner record names what
  that runner provides. A global owner would also admit Docker in files that no runner executes.
- **Build the image from the proposal.** This Change edits no file that the manifest hashes, so the
  image that `supply_image` built from `b350f258e` matches the landed head.

## Risks / Trade-offs

- [A later job runs Docker on a runner that does not declare it] → Reference closure reports an
  orphan consumer in that Forge's file, which is the intended review point.
