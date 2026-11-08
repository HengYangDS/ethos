# Design

## Context

The model's GitHub verification job installs Mise through `jdx/mise-action`, pinned by commit, with
`install: false` and `cache: false`; the Mise version itself comes from the supply policy.

## Goals / Non-Goals

Goals:

- Adopters' rendered workflows install Mise through the newest released `jdx/mise-action`.
- The console stubs of the process tests replace the one dispatch the console calls.

Non-Goals:

- ETHOS's own workflows, which do not run the action, and the Mise version, which the supply policy
  owns.

## Decisions

1. **Pin by commit.** The step names v5.2.7's commit, as the model pins every action. GitHub's tag
   `v5.2.7` names commit `b44d12e7d0d8ee7461bb893e1b1993500433185b`; the release is neither a draft
   nor a prerelease and is the latest.
2. **Inputs unchanged.** v5.2.7 adds no input and changes none (its release notes, and `action.yml`
   is unchanged since v5.2.6), so the step keeps `version`, `install` and `cache`.
3. **Stub the console's one dispatch.** The test's console stub replaces `run_application`, the one
   function the console calls to run a command, instead of `app` and `dispatch_arguments`.

## Risks / Trade-offs

- An adopter's workflow changes only when it regenerates from a release that carries this model.
