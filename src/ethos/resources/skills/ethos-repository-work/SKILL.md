---
name: ethos-repository-work
description: Use installed ETHOS for repository formation or adoption, governed changes, quality, delivery, recovery and feedback; not ETHOS product implementation.
---

# ETHOS Repository Work

This guidance travels with the invoking ETHOS package. It routes repository work,
not maintenance of ETHOS itself. It is a projection, not repository policy,
authorization, proof, or an Agent-specific command channel.

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

Select the relevant source by its `role` in that result; open the advertised
absolute path and selected sections. The package supplies the common contract,
while the target supplies business meaning and native implementation. Do not
copy a contract into another rule, Skill, template or gate to make it available.

| Task                                           | Source roles                      | Method and acceptance boundary                                                                                                                                                                                                 |
| ---------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Understand a problem and align intent          | `product-meaning`, `agent-method` | Preserve source obligations, assumptions and trade-offs in the current official Change. Challenge the interpretation before compiling it; test success cannot establish intent fidelity.                                       |
| Form a new repository or adopt an existing one | `adoption`, `commands`            | Choose explicit creation only for an absent target. For an existing repository, inspect its native owners and current gaps before a reviewable migration. Binding alone does not deliver a usable quality foundation.          |
| Build or revise a capability                   | `product-meaning`, `rules`        | Resolve the invariant, sole owner, consumers and required evidence first. Reuse native capabilities and deep modules; preserve meaning when consolidating or removing paths.                                                   |
| Govern documents and repository structure      | `documentation`, `adoption`       | Apply the common reading, identity and carrier contracts to the selected roots. Keep business taxonomy local; README navigates and Decision Records explain irreducible choices rather than owning task progress.              |
| Verify, integrate and deliver                  | `commands`, `release`             | Execute the applicable native checks once on exact subjects; retain warnings, failures and unknowns. Check combination and per-effect admission; distinguish source proof, installed behavior, publication and actual benefit. |
| Recover, hand off, upgrade or exit             | `recovery`, `commands`            | Observe uncertain effects before replay, preserve unique results and rollback consumers, and rediscover the current package and continuation on handoff. Retire only exact reviewed resources.                                 |
| Learn from outcomes or recurring failure       | `product-meaning`, `agent-method` | Diagnose the failed assumption in the target's business domain, change the effective owner and exercise the distinguishing result. Escalate a model gap instead of repeating a disproved workaround.                           |

Methods may compose; their obligations keep one owner. An available method,
matching route or structural Skills PASS is not complete product coverage.
If a required method, native capability or evidence is absent, keep that exact
gap open in the existing Change and proceed only with independent admitted work.
Optional mature Skills and native OpenSpec commands may supply a method through
their explicit capability contract, never another lifecycle or policy authority.

Before design, use the product-meaning source to review SSOT, DRY, MECE, SOLID,
semantic preservation, deep interfaces and necessity. Before effects, use the
rule reference to resolve the applicable trigger, owner, action, evidence and
stop condition. A matched Skill supplies methods and native tool routing; it
cannot redefine a rule, weaken acceptance or create another progress store.
Repository business intent and authored local guidance retain their owners.

Common governance is not optional merely because a toolchain is local. Compare
the profile's declared native checks with each applicable obligation and actual
subject coverage; investigate disconnected or misbound checks. If an obligation
has no executable owner, report the implementation gap rather than certify it
from this guidance. Extensions preserve the common floor without imposing one
language, model, Agent, directory tree or provider.

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
