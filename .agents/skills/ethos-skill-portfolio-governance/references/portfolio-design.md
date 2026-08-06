# Skill Portfolio Design

Use this reference when improving ETHOS repo-local skills without adding a new
truth center.

## First Principles

- One portfolio, few skills: strengthen an existing subject owner before adding
  another skill.
- MECE subjects: lifecycle, repository governance, skill portfolio, quality
  gates, and adoption profiles have distinct primary reasons to change.
- SSOT: activation routes, package manifests, and SKILL.md front matter agree;
  command JSON and repository files remain truth.
- DRY: put repeated fragile checks in owner scripts and longer judgement
  criteria in references.
- A skill routes work only. It does not create a task store, lifecycle ledger,
  or provider-specific authority.
- OpenSpec owns its generated Skills and slash commands. ETHOS characterizes
  their pinned output and never forks the official workflow templates.
- Matched evaluation is evidence about a route, not progress through a Change.

## Admission

A new skill is justified only when the procedure is repeated,
repository-specific, and cannot fit an existing owner without losing a clear
subject boundary. It needs a package manifest, activation route, digest, and
current owner-script or proof-gate evidence.

An existing skill is retired only after its route has moved or disappeared,
its carrier is removed, and activation metadata records the reason, retirement
date, and observable kill signal.

## Audit Loop

Run the current proof gate and changed-scope plan:

```bash
ethos prove --gate playbooks-v2 --json
ethos plan --changed --json
```
