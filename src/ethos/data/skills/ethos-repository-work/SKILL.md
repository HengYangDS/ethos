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
   result. To create or inspect a Change, execute the current status result's
   `governance_context.official_openspec.base_command` with official OpenSpec
   arguments from the target worktree. Do not assume an ambient `openspec`
   executable or import ETHOS's source-tree instructions into an adopter.
3. For a tracked edit, obtain a passing `ethos lane prewrite` for the exact
   worktree and paths immediately before writing. A Skill, lease, or status
   observation alone grants no mutation authority.
4. After an effect, re-observe through the installed CLI. Treat timeout,
   cancellation, and a lost reply as unknown until the actual effect is checked;
   do not blindly repeat it. Preserve another holder's lane and unreviewed work.

## Common Principles And Task Methods

Use `governance_context.agent_guidance.sources` from the current product result
for common principles and rule references. Open its selected sections first,
then follow only the rule owner needed for the task. These exact references
travel with the installed product; users need not repeat them per repository.
The selection is not a complete ETHOS checkout or a transitive reference bundle.
Use the target's declared profile and rule owners for native implementations;
ETHOS-specific source links do not impose its toolchain on an adopter. A needed
unavailable reference or evidence remains unproved, not implicitly satisfied.

Before design, use the product-meaning source to review SSOT, DRY, MECE, SOLID,
semantic preservation, deep interfaces and necessity. Before effects, use the
rule reference to resolve the applicable trigger, owner, action, evidence and
stop condition. A matched Skill supplies methods and native tool routing; it
cannot redefine a rule, weaken acceptance or create another progress store.
Repository business intent and authored local guidance retain their owners.

For parallel work, read the accepted intent's allowed combinations and retention
conditions before choosing contributions. Separate selection from preservation:
check retained results and handoff evidence before retiring a declined lane through
the current lifecycle command. A preserved result need not keep its worktree alive.

On upgrade, target change or Agent handoff, rediscover current references and
continuation. File availability and matching hashes establish source access,
not that an Agent loaded, understood or followed the guidance. Exercise the
accepted task journey before making that behavioral claim.

Follow the current result rather than a memorized command sequence. A proposed
next action is not proof that its prerequisites have already been satisfied.
