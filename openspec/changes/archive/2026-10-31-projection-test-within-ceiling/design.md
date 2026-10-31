# Design

## Context

See [proposal.md](proposal.md). The fault replaces the floor's text in the copied Mise configuration
and expects the CUE owner to refuse the mismatched bootstrap record. A literal that no longer
matches leaves the configuration unchanged, so the expected refusal does not occur and the case
fails; the literal cannot go stale silently.

## Goals / Non-Goals

**Goals:**

- The module is within the ceiling and the fault still exercises the moved floor.

**Non-Goals:**

- Splitting the module by semantic ownership. It is now exactly at the ceiling, so the next change
  that adds a line to it splits it.

## Decisions

- **Name the floor rather than split the module now.** The literal costs one edit per Mise move and
  fails loudly when stale; the split belongs to a change that adds behavior to the module.

## Risks / Trade-offs

- [The next Mise move forgets the literal] → The fault case then fails in the proof, as described
  above.
