---
subject: ethos:adoption-profiles
role: explanation
state: canonical
relations:
  canonical_for: repository adoption
---

# Adoption Binding

Status: canonical.

Purpose: explain how ETHOS binds an adopter without cloning product governance
or inventing repository-type profiles.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), [Glossary](../reference/glossary.md), [Repository Profile Contract](../governance/repository-profile-contract.md), and [Config Boundary Model](../governance/config-boundary-model.md).

`ethos adopt` has one declaration-first path. A read-only invocation plans one
tracked file:

```text
.ethos/profile.toml
```

The strict frozen repository-profile declaration owns both in-memory validation
and TOML serialization. It binds a non-empty adopter identity and non-empty
OpenSpec material paths. Existing unrelated files are outside adoption scope;
a differing nonempty binding file is a blocking conflict and is never merged,
overlaid, aliased, or migrated implicitly.

```bash
ethos adopt --root <repo> --json
ethos adopt --root <repo> --apply --authorize --expect-head <git-head> --json
```

The first command reports the exact plan, apply criteria, conflicts, and
rollback instructions. The second writes the binding only after explicit
authorization and HEAD matching. Optional capabilities are created later by
their own owners: OpenSpec by OpenSpec, docs by docs tooling, skills by skill
governance, and GitHub or GitLab CI by provider projection tooling.

The declaration may point at existing repository-owned roots such as `.config/`,
`rules/`, `openspec/`, `docs/`, `evidence/`, and `.agents/skills/`. Their
presence is capability state, not a bootstrap prerequisite. Branch-role names,
domain gates, provider state, and tool-native configuration remain adopter
facts; adoption does not generate or normalize them.

An adopted repository uses the same result and continuation semantics as the
product. The profile selects repository-owned facts and gates; it does not
create a second command plane or copy adopter semantics into the ETHOS product
runtime.

Product release policy is likewise profile-bounded. Merely having a
`pyproject.toml` does not make an adopter an ETHOS Python workspace. A
runtime-files adopter may keep its release name, distribution kind, Python
floor, and `VERSION` path under one repository-owned `[tool.<name>]` table;
ETHOS reads that declared identity without requiring a synthetic `[project]`
table or applying product-only release surfaces during generic audits.
