# Skill Portfolio Design

Use this reference when improving ETHOS repo-local skills without adding a new
truth center.

## First Principles

- One portfolio, few skills: prefer strengthening an existing skill before
  creating another one.
- MECE subjects: lifecycle, repository governance, skill portfolio, quality
  gates, and adoption profiles should cover the common procedures without
  overlapping ownership.
- SSOT: activation routes, package manifests, and SKILL.md frontmatter must
  agree; command JSON and repository files remain truth.
- DRY: put repeated fragile checks in `scripts/`; put longer judgement criteria
  in `references/`; keep `SKILL.md` short.
- SOLID: each skill owns one reason to change and exposes narrow commands,
  evidence, and trust boundary.
- Route ownership is exact and visible: duplicate exact `path_globs`, weak
  trigger descriptions, oversized entrypoints without `references/` or
  `scripts/`, stale package digests, and missing `changed-scope` are hard gaps.

## Skill Creator Use

Skill creation is an admission workflow inside this portfolio owner, not a
separate primary skill. Treat a proposed skill as a change request and admit it
only when all are true:

1. The procedure is repeated and repository-specific.
2. Existing skills cannot own it without losing MECE boundaries.
3. The new skill can stay small and point to repository truth.
4. It has a package manifest, activation route, evidence commands, and digest.
5. It owns a durable semantic obligation rather than a vendor surface, UI affordance,
   or one-off workaround.

If any condition fails, update docs, rules, scripts, or references inside an
existing skill instead. A creator helper may scaffold files, but the portfolio
owner must still decide admission through activation coverage, package integrity,
projection drift, and changed-scope routing evidence.

Use this minimal admission checklist before adding a skill:

```text
trigger -> owner subject -> existing-skill fit -> truth boundary -> package manifest
  -> activation route -> digest -> proof commands -> projection drift check
```

## Multi-agent Boundary

Do not use skill changes to route around Work Lane coordination. If another
agent owns an overlapping dirty scope, preserve that lane and move to a disjoint
improvement or wait for integration.

## Audit Loop

Use `ethos playbooks check --mode v2-strict --json` to inspect
`portfolio_coverage` and `portfolio_design`. The first proves the required
primary subjects exist once; the second proves route ownership remains MECE and
entrypoints stay loadable.

Run the bundled audit before claiming portfolio readiness:

```bash
.agents/skills/ethos-skill-portfolio-governance/scripts/portfolio_audit.py .
```

Then run the repository gates:

```bash
ethos playbooks check --mode v2-strict --json
ethos prove --gate playbooks-v2 --json
ethos playbooks route --changed --json
```
