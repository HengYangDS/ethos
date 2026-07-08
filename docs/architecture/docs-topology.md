---
subject: ethos:docs-topology
role: reference
state: canonical
relations:
  canonical_for: documentation topology contract
---

# Documentation Topology

Status: canonical.

Purpose: define the minimal semantic documentation kernel shared by ETHOS and
repositories governed by ETHOS.

See also: [Documentation Root](../README.md), [Docs Registry](../governance/docs-registry.md),
[Decision Records](../decisions/README.md), and
[Minimal Semantic Documentation Topology Decision](../decisions/accepted/DR-0004-native-documentation-topology-contract.md).

## Contract

ETHOS requires a small common docs kernel across governed repositories so humans
and agents can recover decisions, evidence, reference vocabulary, and history
without learning a new information architecture for every repository.
Documentation is organized on two bound axes: a directory names a document's
subject domain, while its `role` front matter names the document's function. A
role must be legal for its directory — kernel roles (`decision`, `evidence`,
`history`, `reference`) are bound to their lanes everywhere, and product or
adopter extension roots declare the roles they accept in the taxonomy. Lifecycle
state is declared with the explicit state vocabulary and backed by HEAD-bound
evidence. `current` and `future` are not valid documentation state values and
must not be encoded as docs roots.

The contract is about semantic isomorphism, not physical uniformity. Governed
repositories share the same decision/evidence/reference/history recovery
kernel, while product or domain roots remain extensions owned by the repository
that declares them.

Required paths:

| Path | Boundary |
| --- | --- |
| `docs/README.md` | documentation navigation and semantic lane map |
| `docs/decisions/README.md` | durable decision-record entrypoint |
| `docs/decisions/decision-index.md` | accepted ruling index |
| `docs/decisions/decision-dependency-map.md` | dependencies between durable rulings |
| `docs/decisions/decision-code-links.md` | links from rulings to code, tests, commands, and evidence |
| `docs/decisions/accepted/README.md` | accepted decision records |
| `docs/decisions/superseded/README.md` | superseded decision records |
| `docs/decisions/templates/README.md` | decision-record template index |
| `docs/decisions/templates/decision-record.md` | decision-record template |
| `docs/evidence/README.md` | dated proof and scoped evidence summaries |
| `docs/history/README.md` | retired rationale and archival logs |
| `docs/reference/README.md` | stable vocabulary, boundaries, and governance references |

Forbidden roots:

| Path | Reason |
| --- | --- |
| `docs/current/` | encodes present truth in topology instead of state metadata and HEAD-bound evidence |
| `docs/future/` | encodes unlanded intent in topology instead of OpenSpec, plans, research, or promotion status |

The required kernel is repository-form invariant: a single repository, monorepo,
or multi-repository governed subject uses the same required docs paths. The
contract does not force all repositories to use identical subject matter or
product extension roots. ETHOS product roots such as `docs/architecture/`,
`docs/concepts/`, `docs/governance/`, `docs/plans/`, `docs/research/`, and
`docs/start/` may exist as product extensions; adopter repositories may add
domain-specific subtrees. The common minimal semantic kernel remains stable.
Extension roots do not become mandatory adoption requirements merely because
the ETHOS product repository uses them.

## Audit

```bash
ethos quality docs-topology --json
```

The audit reports missing required docs-kernel paths, forbidden `current`/`future`
roots, and visible ETHOS product extension roots. It is a proof gate:

```bash
ethos prove --execute --gate docs-topology --expect-head <git-head> --json
```

## Adoption

`ethos adopt` scaffolds the minimal semantic common kernel for new adopters
and may add first-run or governance extension docs when useful. Existing
adopters must
converge toward the same kernel before embedded ETHOS retirement can be claimed,
because retirement depends on shared evidence/decision/reference routing and
explicit state metadata, not just passing runtime tests.

`ethos fleet retirement-readiness --target <repo> --root <product> --json`
therefore treats `ethos quality docs-topology --root <repo> --json` gaps as
blocking retirement gaps. A repository may keep richer domain-specific docs, but
it cannot retire an embedded ETHOS backend while the minimal semantic common docs kernel is
missing or using forbidden `current`/`future` documentation roots.
