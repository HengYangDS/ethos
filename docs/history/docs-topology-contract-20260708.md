---
subject: ethos:history:docs-topology-contract-20260708
role: history
state: superseded
relations:
  historical_carrier_for: DR-0004 native documentation topology contract
  current_owner: ../governance/docs-registry.md
---

# Historical Carrier: Documentation Topology

Status: historical and superseded.

Purpose: preserve the rationale and contract of the former fixed-path
`docs-topology` capability. This carrier is not current authority. The
current reusable owner is the [Docs Registry](../governance/docs-registry.md);
ETHOS's own physical documentation shape is handled by the ETHOS repository
self-audit. No replacement Decision Record was created.

Historical decision record: [DR-0004](../decisions/DR-0004-native-documentation-topology-contract.md).

## Historical Contract

The former docs-topology capability audited one repository-form-invariant
recovery kernel. Directories named subject domains, while `role` front matter
named a document's function. Kernel roles (`decision`, `evidence`,
`history`, `reference`) were bound to their lanes. Lifecycle state was
explicit metadata backed by repository evidence; `current` and `future`
were neither valid state values nor valid documentation roots.

The former required paths were:

| Path | Historical boundary |
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

The former forbidden roots were:

| Path | Historical reason |
| --- | --- |
| `docs/current/` | encoded present truth in topology instead of state metadata and HEAD-bound evidence |
| `docs/future/` | encoded unlanded intent in topology instead of OpenSpec, plans, research, or promotion status |

There was no compatibility policy, mapped status vocabulary, alternate root set,
or repository-form exception. Single repositories, monorepos, and
multi-repository subjects used the same kernel whenever the capability was
executed. Product or domain roots such as `docs/architecture/`,
`docs/concepts/`, `docs/governance/`, `docs/plans/`,
`docs/research/`, and `docs/start/` remained optional extensions.

## Historical Knowledge Lifecycle

Retirement was the last step of semantic convergence, not a substitute for it.
Every source carrier followed this ordered lifecycle:

| Phase | Required result |
| --- | --- |
| Preserve | Inventory the carrier and protect immutable history and evidence. |
| Extract | Identify each independent rule, decision, fact, rationale, scenario, and unresolved question. |
| Place | Bind every extracted item to one current authority owner or historical carrier. |
| Integrate | Rewrite the owner so the useful meaning was coherent in its current taxonomy, vocabulary, and organization. |
| Verify | Prove semantic coverage, valid links, scenario preservation, and absence of conflicting current owners. |
| Retire | Remove only the residual carrier that had no independent current, historical, or evidentiary value. |

The historical allowed destinations were:

| Meaning | Destination |
| --- | --- |
| current normative contract | canonical architecture, governance, reference, or start documentation |
| durable ruling | accepted or superseded decision record |
| factual chronology or retired rationale | `docs/history/`, explicitly non-normative |
| change proposal and delta history | active or archived OpenSpec carrier |
| execution or recovery proof | repository-family evidence or recovery record |
| fully absorbed repetition | deletion after verification |

An item that did not fit the current taxonomy without semantic loss was a model
gap, not deletion residue. Retirement stopped while the responsible ontology,
taxonomy, contract, or boundary was raised to contain the new distinction.
Historical carriers preserved facts but could not issue current instructions.

## Retired Audit Surface

The former audit surface included these historical command examples:

    ethos prove --gate docs-topology --json
    ethos prove --execute --gate docs-topology --expect-head <git-head> --json
    ethos prove --gate docs-topology --root <repo> --json

These examples are historical only. They are not current commands, current gates,
or instructions to execute. Current documentation quality is owned by the
portable Docs Registry; ETHOS's own physical documentation quality is owned by
its repository self-audit.

## Adoption And Retirement

The former `ethos adopt` behavior wrote only `.ethos/profile.toml`; it
neither created nor implicitly activated documentation topology. Missing docs
carriers therefore did not block the default adopter proof floor.

The former capability is retired. Its fixed-path requirements no longer define
adopter conformance, and this carrier must not be cited as current authority.
