---
subject: ethos:docs-topology
role: reference
state: canonical
relations:
  canonical_for: documentation topology contract
---

# Documentation Topology

Status: canonical.

Purpose: define the high-isomorphism semantic documentation kernel shared by
ETHOS and repositories governed by ETHOS.

See also: [Documentation Root](../README.md), [Docs Registry](../governance/docs-registry.md),
[Decision Records](../decisions/README.md), and
[Documentation Topology Decision](../decisions/accepted/DR-0002-documentation-topology-isomorphism-contract.md).

## Contract

ETHOS requires a common docs kernel across governed repositories so humans and
agents can recover governance, evidence, decisions, plans, references, and
history without learning a new information architecture for every repository.
Directory names describe semantic ownership. Lifecycle state is declared in
front matter and backed by evidence; it is not encoded as `current/` or
`future/` path topology.

Required paths:

| Path | Boundary |
| --- | --- |
| `docs/README.md` | documentation navigation and semantic lane map |
| `docs/index.md` | audience-oriented documentation navigation |
| `docs/start/quickstart.md` | first-run workflow and command path |
| `docs/governance/README.md` | governance policy and operating model index |
| `docs/decisions/README.md` | durable decision-record entrypoint |
| `docs/decisions/decision-index.md` | accepted ruling index |
| `docs/decisions/decision-dependency-map.md` | dependencies between durable rulings |
| `docs/decisions/decision-code-links.md` | links from rulings to code, tests, commands, and evidence |
| `docs/decisions/accepted/README.md` | accepted decision records |
| `docs/decisions/superseded/README.md` | superseded decision records |
| `docs/decisions/templates/README.md` | decision-record template index |
| `docs/decisions/templates/decision-record.md` | decision-record template |
| `docs/evidence/README.md` | dated proof and scoped evidence summaries |
| `docs/plans/README.md` | planned work and roadmap material with explicit state |
| `docs/history/README.md` | retired rationale and archival logs |
| `docs/reference/README.md` | stable vocabulary, boundaries, and governance references |

Forbidden roots:

| Path | Reason |
| --- | --- |
| `docs/current/` | encodes truth state in topology instead of metadata and evidence |
| `docs/future/` | encodes plan state in topology instead of metadata and promotion status |

The required kernel is repository-form invariant: a single repository, monorepo,
or multi-repository governed subject uses the same required docs paths. The
contract does not force all repositories to use identical subject matter or
product extension roots. ETHOS product roots such as `docs/architecture/`,
`docs/concepts/`, and `docs/research/` may exist as product extensions; adopter
repositories may add domain-specific subtrees. The common semantic kernel remains
stable.

## Audit

```bash
ethos quality docs-topology --json
```

The audit reports missing required docs-kernel paths, forbidden time-state roots,
and visible ETHOS product extension roots. It is a proof gate:

```bash
ethos prove --execute --gate docs-topology --expect-head <git-head> --json
```

## Adoption

`ethos adopt` scaffolds this semantic docs kernel for new adopters. Existing
adopters must converge toward the same kernel before embedded ETHOS retirement
can be claimed, because retirement depends on shared governance/evidence/decision
routing and explicit front matter state, not just passing runtime tests.

`ethos fleet retirement-readiness --target <repo> --root <product> --json`
therefore treats `ethos quality docs-topology --root <repo> --json` gaps as
blocking retirement gaps. A repository may keep richer domain-specific docs, but
it cannot retire an embedded ETHOS backend while the common docs kernel is
missing, structurally divergent, or using forbidden time-state documentation
roots.
