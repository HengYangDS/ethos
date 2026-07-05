---
subject: ethos:playbooks-skills
role: policy
state: canonical
relations:
  canonical_for: repo-local skill projection
---

# Playbooks And Skills

Repo-local skills are ETHOS playbook projections. They help agents choose the
right command, document, schema, or evidence path, but they do not become a new
source of truth. Repository truth remains source code, tests, schemas, current
docs, promoted OpenSpec records, claims, evidence, and command JSON.

The canonical local layout is:

```text
.agents/skills/
  README.md
  activation.toml
  <skill-id>/
    SKILL.md
    package.toml
```

`activation.toml` is the ETHOS activation registry input. It is not a
provider-native skill file. It records route subjects, changed-path coverage,
operation metadata, lifecycle, package manifest paths, proof obligations,
co-activation hints, and command affordances. ETHOS normalizes this input into a
provider-neutral Skills V2 registry. Inputs without the current registry shape
are reported as required gaps, not compatibility routes.

Each `.agents/skills/<skill-id>/SKILL.md` must still be a real loadable workflow
package. The package must have official skill frontmatter, explicit trigger
boundaries, workflow steps, evidence guidance, and a trust-boundary section.
`package.toml` binds that provider-visible package to included files, required
sections, expected digest, and declared capability classes. The manifest is
package inventory and integrity metadata; activation authority stays in the
ETHOS activation registry.


## Portfolio Shape

The product skill portfolio is intentionally small and MECE:

- `ethos-change-lifecycle` owns the transition loop.
- `ethos-repository-governance` owns repository authority and governance routing.
- `ethos-skill-portfolio-governance` owns meta-skill creation, validation,
  projection drift, and retirement.
- `ethos-quality-gate-governance` owns quality gate and provider-projection
  convergence.
- `ethos-adoption-profile-governance` owns product/adopter profile isomorphism.

Do not add surface-specific skills for CLI, GitLab, MCP, editor hosts, or model
providers unless a repeated repository-specific procedure cannot be represented
by one of these subjects. Prefer references or scripts inside the existing skill
package before adding a new skill.

Playbook checks fail closed in strict mode:

- `v2-strict` fails closed for product proof when activation metadata, package
  manifests, digest state, path coverage, proof obligations, or skill package
  quality are missing.

`ethos playbooks check --mode v2-strict --json` validates the ETHOS product-root
projection. `ethos playbooks check --root <repo> --json` uses the same strict
contract for external adopter inspection. `ethos playbooks route --changed
--json` uses explicit changed-scope subjects and path-glob evidence rather than
substring matching alone.

Assistant host memory, local sessions, MCP servers, and provider-specific
prompts remain context providers or adapters. Durable guidance must be promoted
into source, tests, schemas, docs, OpenSpec records, claims, or evidence.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
