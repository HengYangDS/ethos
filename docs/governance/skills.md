---
subject: ethos:skills
role: policy
state: canonical
relations:
  canonical_for: repo-local skill projection
---

# Repo-local Skills

Status: canonical.

Purpose: define `.agents/skills/` as the canonical repository-local skill
portfolio and keep skill procedures below repository truth.

See also: [Skill Rules](../../rules/skills.md) and
[Repo-local Skills](../../.agents/skills/README.md).

Skills route agents to current owner scripts, proof gates, rules, docs, and
repository facts. They do not create a task system, command plane, lifecycle
ledger, or source of truth. Each skill has one narrow subject, a manifest, and
an activation route.

Two projection families remain distinct:

- `.agents/skills/` contains narrow ETHOS procedures routed by
  `.agents/skills/activation.toml`.
- The pinned official OpenSpec workflow generates each admitted host's native
  OpenSpec Skills and, where the host supports them, slash commands. ETHOS does
  not copy, template, or fork those artifacts.

OpenSpec status, instructions, artifact dependencies, tasks, and archive
lifecycle remain authoritative for the Change. Generated Skills and commands
only expose that official workflow to an agent host. Superpowers and other
method packs are optional; they own no plan, task, progress, or lifecycle state.

The portfolio owner is responsible for structural validation:

```bash
ethos prove --gate skills --json
ethos plan --changed --json
```

Repo-local skills must call current owner scripts or current proof gates. They
must not preserve removed command roots, copy policy into a shadow procedure,
or record durable task state outside tracked repository authority.

Portfolio evolution is executable rather than editorial: every active route
has one semantic owner; duplicate subjects, commands, globs, intent tokens, or
subject-operation routes are reported; retired entries name their reason,
date, kill signal, and optional removed carrier; matched evaluations remain
evidence metadata and cannot encode completion or progress.

At each lifecycle node ETHOS compiles current operation, subject, and changed
paths into zero or more Skills. Exact `requires` edges form the dependency
closure; `excludes` conflicts and missing or cyclic requirements fail closed.
The projection carries only the ordered Skill identities and deduplicated
pre-reads, rules, and post-checks needed for that node.

Host-native files are projections unless their host owns an official native
artifact. Repository source, tests, schemas, docs, OpenSpec, effective
Commitments, Attestations, and current command JSON remain authoritative.

## Learning And Behavioral Qualification

[Feedback Closure](../../rules/agents.md#feedback-closure) owns the execution
discipline. OpenSpec owns accepted obligations and progress; native policy and
implementation own enforceable behavior; a skill supplies reusable procedure.
Documentation explains the choice without copying a second rule or task ledger.

The `skills` gate establishes package, schema, routing and declared relationship
integrity. It does not prove that an agent loaded the projection, understood the
source, followed it or improved an outcome. A skill change needs a representative
trigger, a non-trigger or conflicting case, and a replay of the behavior it is
intended to change. Record those observations in existing verification evidence.
Do not call a structural PASS, a longer skill or a larger portfolio learned behavior.

Repair missed triggers and ineffective guidance at their existing owner; remove
superseded instructions and retire overlap only after consumer review. A new
skill is justified by an otherwise uncovered reusable procedure, not by the
arrival of another feedback message. Host loading and installed projection
qualification remain distinct from source-side package validation.
