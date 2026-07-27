---
subject: ethos:docs-topology
role: reference
state: canonical
relations:
  canonical_for: documentation topology contract
---

# Documentation Topology

Status: canonical.

Purpose: define the strict semantic documentation kernel used when the
docs-topology capability is selected.

See also: [Documentation Root](../README.md), [Docs Registry](../governance/docs-registry.md),
[Decision Records](../decisions/README.md), and
[Minimal Semantic Documentation Topology Decision](../decisions/accepted/DR-0004-native-documentation-topology-contract.md).

## Contract

The docs-topology capability audits one repository-form-invariant recovery
kernel. Directories name subject domains, while `role` front matter names a
document's function. Kernel roles (`decision`, `evidence`, `history`,
`reference`) remain bound to their lanes. Lifecycle state is explicit metadata
backed by repository evidence; `current` and `future` are neither valid state
values nor valid documentation roots.

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

There is no compatibility policy, mapped status vocabulary, alternate root set,
or repository-form exception. Single repositories, monorepos, and
multi-repository subjects use this same kernel whenever the capability is
executed. Product or domain roots such as `docs/architecture/`,
`docs/concepts/`, `docs/governance/`, `docs/plans/`, `docs/research/`, and
`docs/start/` remain optional extensions.

## Absorptive Knowledge Lifecycle

Retirement is the last step of semantic convergence, not a substitute for it.
Every source carrier follows one ordered lifecycle:

| Phase | Required result |
| --- | --- |
| Preserve | Inventory the carrier and protect immutable history and evidence. |
| Extract | Identify each independent rule, decision, fact, rationale, scenario, and unresolved question. |
| Place | Bind every extracted item to one current authority owner or historical carrier. |
| Integrate | Rewrite the owner so the useful meaning is coherent in its current taxonomy, vocabulary, and organization. |
| Verify | Prove semantic coverage, valid links, scenario preservation, and absence of conflicting current owners. |
| Retire | Remove only the residual carrier that has no independent current, historical, or evidentiary value. |

The allowed destinations are deliberately narrow:

| Meaning | Destination |
| --- | --- |
| current normative contract | canonical architecture, governance, reference, or start documentation |
| durable ruling | accepted or superseded decision record |
| factual chronology or retired rationale | `docs/history/`, explicitly non-normative |
| change proposal and delta history | active or archived OpenSpec carrier |
| execution or recovery proof | repository-family evidence or recovery record |
| fully absorbed repetition | deletion after verification |

An item that does not fit the current taxonomy without semantic loss is a model
gap, not deletion residue. Retirement stops while the responsible ontology,
taxonomy, contract, or boundary is raised to contain the new distinction. The
source carrier becomes retireable only after the higher-order design absorbs
the conflicting meanings and their original scenarios pass.

Do not create a generic archive, copy a document as a backup, or leave a lower
order carrier linked from a current index. Historical carriers preserve facts
but cannot issue current instructions. OpenSpec archives and repository-family
records remain immutable in their owner-native lifecycle.

## Audit

```bash
ethos prove --gate docs-topology --json
```

The same strict audit may be selected explicitly in proof:

```bash
ethos prove --execute --gate docs-topology --expect-head <git-head> --json
```

## Adoption And Retirement

`ethos adopt` writes only `.ethos/profile.toml`; it neither creates nor
implicitly activates documentation topology. Missing docs carriers therefore do
not block the default adopter proof floor.

`ethos prove --gate docs-topology --root <repo> --json` selects this
capability. At that boundary the complete kernel is required and `docs/current/`
or `docs/future/` blocks retirement.
