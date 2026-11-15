# Design

## Context

`adopt_existing` resolves the adopted root and renders every continuation with it:
`ethos status --root <root> --json` after an apply, and `ethos adopt --root <root> ...` before one.
The one continuation without the root is the relock after an apply that wrote the pin, the bare
`mise lock`. Mise selects its configuration from the working directory unless `--cd` names one.
The product's other Mise next actions name it: the locked install of a pinned release, the trust
of a configuration, and the bootstrap after a closeout.

The accepted requirement states both halves: the caller's working directory does not change the
selection, and the continuation is the bare command, "which the caller runs in the adopted root".
The second half leaves the selection to the caller.

## Goals / Non-Goals

Goals:

- The relock locks the adopted repository from any working directory.

Non-Goals:

- Running the relock inside `ethos adopt`. Locking contacts the network and writes the lockfile,
  and the release-candidate design keeps that step with the caller.
- Changing the conflict's repair text or the prose that names the lockfile's writer.

## Decisions

1. **The relock names the adopted root with `--cd`.**
   - **Rests on:** the owner's decision of 2026-11-15; the requirement's scenario
     `Adoption succeeds outside the target working directory`; three next actions in the product
     that already use `mise --cd <root>`.
   - **Considered:** keeping the bare command, the text approved with `adopt-pin`; and a sentence
     of prose that tells the caller to change directory first.
   - **Chosen because:** an agent runs a next action as written, often from a directory other
     than the repository. The bare command then locks another configuration or fails, and prose
     cannot be executed.
   - **Applies to:** the next action of an applied adoption that wrote the pin. An adoption that
     kept the Mise configuration continues with status, as before.
2. **The step stays an instruction.**
   - **Rests on:** `derive_next_step`, which gives a command's structure only to an exact
     invocation of the product.
   - **Considered:** a structured step with an argument vector for the Mise command.
   - **Chosen because:** the step's vocabulary describes the product's own operations, their
     effects and their authorization; a foreign tool's command has no entry there.
   - **Applies to:** `next.kind` of the applied result, which the regression keeps.

## Risks / Trade-offs

- A reader that compared the next action with the literal `mise lock` no longer matches. The bare
  form is in no released build, and the unreleased changelog entry is corrected in this Change.
- The root is rendered as the product renders it for `--root` in the same result, quoted by the
  same function.
