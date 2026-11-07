# Design

## Context

See [proposal.md](proposal.md). The design record is
`build/runtime/work/hardening/post-beta6-hardening-draft.md`, section 2, as amended by its decision
of 09:5x. `_protection_reasons` already checks branch, lock, audit root, existence, cleanliness and
the temporary roots. A worktree passes housekeeping's reobservation before removal only when it is
still removable.

## Goals / Non-Goals

Goals:

- Housekeeping never removes the only copy of a commit or of ignored content.

Non-goals:

- Removing protected worktrees. An operator makes a ref, or removes them with native Git.

## Decisions

- **Retaining refs only.** `git for-each-ref --count=1 --contains=<HEAD>` runs over `refs/heads`,
  `refs/tags`, `refs/remotes` and `refs/keep`. `refs/stash` and foreign refs, such as
  `refs/codex/snapshots`, do not vouch for a commit. `rev-list --all` is not used, because it counts
  every worktree's own `HEAD`.
- **Ignored content by native Git.** Housekeeping lists the worktree's ignored entries with
  `git ls-files --others --ignored --exclude-standard --directory`. A root `.venv/`, a root
  `node_modules/`, and a `__pycache__/` whose files are all `.pyc` beside their own source are
  regenerable. Anything else protects the worktree. The residue-class design owns this root list.
- **Only otherwise removable entries pay.** The checks run after every existing reason, at
  inventory and at the reobservation before removal.

## Risks / Trade-offs

- More worktrees stay protected until an operator acts.
- `--contains` walks from every retaining ref, and its cost at ETHOS's ref count is unmeasured.
