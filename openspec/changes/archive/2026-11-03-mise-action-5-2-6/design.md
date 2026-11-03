# Design

## Context

See [proposal.md](proposal.md). The model's GitHub verification job runs the action with an
explicit Mise version and with installation and caching off, so the action only provides Mise.

## Goals / Non-Goals

**Goals:**

- The shipped model selects the latest stable `jdx/mise-action`, pinned by commit.

**Non-Goals:**

- Changing the Mise version or the job's inputs.

## Decisions

- **Pin the release commit.** `gh api repos/jdx/mise-action/git/ref/tags/v5.2.6` names commit
  `f5be966e4a917d54244728e6a5fdcd1d93a35e6c`, as every action in the model is pinned.

## Risks / Trade-offs

- [5.2.6 changes the action's inputs] → Its release fixes the cache restore only, and the model
  test still checks the inputs that the job passes.
