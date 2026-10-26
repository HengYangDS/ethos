# Design

## Context

See [proposal.md](proposal.md).

- **Isolated resolution.** `tools/ci/toolchain/native.py` provisions the declared tools through ETHOS's native supply. It resolves them on an isolated copy of the configuration in mise's safe mode, and it carries trust to that copy only when native mise reports the root trusted (`carried_trust`).
- **mise's own rule.** On an untrusted copy outside CI mode, mise ignores the copy's lock URLs, and `--locked` then refuses. Any CI marker makes mise trust every configuration. a225 reproduced both outcomes on macOS with mise 2026.10.19:
  - untrusted with safe mode fails;
  - a trusted copy succeeds, and so does `CI=true`.
- **The environment.** CI jobs run with `CI=true`. A Docker build inherits nothing from its runner, so the prepare and smoke stages ran outside CI mode.

## Goals / Non-Goals

**Goals:**

- The supply image builds from the accepted lock, with `--locked` resolution and the recorded checksums.
- The smoke stage accepts the supply under the same CI mode as the jobs that use it.

**Non-Goals:**

- Changing ETHOS's trust carriage, or trusting configurations outside CI.
- Changing the shipped supply stage's environment.

## Decisions

- **`CI=true` in prepare and smoke only.** These stages are CI work: the image build runs in the hosted `supply_image` job, and smoke mirrors the CI bootstrap. The shipped stage stays without it, because jobs set it.
- **Not a trust record or `MISE_TRUSTED_CONFIG_PATHS`.**
  - `run_command` removes `MISE_*` variables, and `mise trust --show` does not count the variable.
  - A trust record would add host state to the build for what the CI marker already declares.

## Risks / Trade-offs

- [CI mode trusts every configuration in those stages] → The stages copy only the repository's own accepted configuration. Its files are the exact inputs hashed into `input.sha256`.
- [Delivery needs a published image] → Section 2 of the tasks owns it: the hosted build, the pinned digests, and green hosted verification on both peers.
