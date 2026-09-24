---
name: ethos-repository-work
description: Use when an installed ETHOS product governs the target repository.
---

# ETHOS Repository Work

This guidance travels with the invoking ETHOS package. It is a projection, not
repository policy, authorization, proof, or an Agent-specific command channel.

1. Run `ethos status --root <repository> --json`. Read `verdict`,
   `required_gaps`, `next_action`, `continuation`, and `user_decision_required`
   together. An empty `next_action` does not mean the product or task is done.
2. Read the target repository's `AGENTS.md` when present, its accepted OpenSpec
   Change, and the rules or documents selected by that repository's current
   result. Do not import ETHOS's source-tree instructions into an adopter.
3. For a tracked edit, obtain a passing `ethos lane prewrite` for the exact
   worktree and paths immediately before writing. A Skill, lease, or status
   observation alone grants no mutation authority.
4. After an effect, re-observe through the installed CLI. Treat timeout,
   cancellation, and a lost reply as unknown until the actual effect is checked;
   do not blindly repeat it. Preserve another holder's lane and unreviewed work.

Follow the current result rather than a memorized command sequence. A proposed
next action is not proof that its prerequisites have already been satisfied.
