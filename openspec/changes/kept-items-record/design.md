# Design

## Context

See the [proposal](proposal.md). A kept ref is an ordinary Git ref under `refs/keep/`; the
product makes none and records nothing when one is deleted. The accepted requirement "Detached
temporary worktree housekeeping is fail-closed" counts kept refs among the refs that retain a
detached worktree's head, so a deletion can change what that housekeeping may remove.

## Goals / Non-Goals

Goals:

- The rule stands in one tracked place, with the reason for each of the 15 refs' present state.
- The five deletions have a tracked statement of what each ref is and where its content stands.

Non-Goals:

- A deletion inside this Change.
- A decision on the seven refs whose content the accepted history lacks.
- A check or a command that enforces the rule.

## Decisions

1. **The rule is a decision record and no requirement.**
   - **Rests on:** the freeze, which admits no new rule, and the rule's subject: what a session
     may leave beside the accepted history.
   - **Considered:** a requirement with a report of kept items.
   - **Chosen because:** a report is a product function with its own design; the record binds
     this repository's sessions now and says so.
   - **Applies to:** `docs/decisions/`.
2. **The record names each ref with its commit and states its evidence itself.**
   - **Rests on:** a tracked record cannot rest on a local file, and a deletion with the
     expected old value needs that value written down.
   - **Considered:** a reference to the local reading.
   - **Chosen because:** the reading is local to one checkout and the record is not.
   - **Applies to:** the record's Decision and Evidence sections.
3. **The evidence is read again at the lane's head before the record is committed, and again
   in the hour of the deletion.**
   - **Rests on:** the accepted branch has grown since the first reading; it can only add
     commits, and the record still states a reading.
   - **Considered:** carrying the first reading alone.
   - **Chosen because:** a stated reading is repeated where it is stated.
   - **Applies to:** the record's Evidence section and the step after the landing.

## Risks / Trade-offs

- After Git's collection the five tips cannot be recovered on this host. The record's evidence
  is the reason that nothing is lost: every commit's content stands in the accepted history.
- Before the deletion, the detached worktrees whose head only one of the five refs reaches are
  listed; on 2026-11-22 this repository has none.
