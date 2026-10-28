---
subject: ethos:decision:one-obligation-one-owner
role: decision
state: canonical
decision_id: DR-0017
decision_status: accepted
relations:
  current_owner: ../../openspec/specs/quality/spec.md
---

# DR-0017: One Obligation, One Owner

Status: canonical rationale. The quality and repository paradigm specifications own current
behavior.

Date: 2026-10-28.

Purpose: preserve why each obligation has one owner across ETHOS and every governed repository, and
why ETHOS judges its own tree by the obligations it ships for every repository.

See also: [DR-0012: Repository paradigm](dr-0012-repository-paradigm.md), the
[quality specification](../../openspec/specs/quality/spec.md), the
[repository paradigm specification](../../openspec/specs/repository-paradigm/spec.md) and the
`shared-quality-obligations` OpenSpec Change.

## Context

DR-0012 made ETHOS own what governed repositories share. On 2026-10-28 ETHOS itself still held two
exceptions:

- The resolver had a second path, `product_source`. A registry at `system/gates.toml` whose history
  the running build shared skipped the shared quality floor and judged dependency acceptance by its
  own committed policy, so a registry path and a merge base decided which obligations applied.
- The packaged `system/gates.toml` mixed the obligations every repository runs with 29 gates that
  serve only ETHOS. An adopter that named one of them got `proof_gate_not_importable`.

Governed repositories include documentation repositories, which carry no tools or tests of their
own and rely on ETHOS for everything they share. The repositories' owner directed that the
essential commonality of governed repositories sink into ETHOS, that no repository build it again,
and that no repository's own business move into ETHOS, with a decidable boundary stated as positive
constraints.

## Decision

Each obligation has one owner across ETHOS and every governed repository:

- ETHOS, when its rule is the same for every repository: a function of observed facts and declared
  values over every configuration the contract admits;
- the repository, for the gates that express its own purpose, which ETHOS runs and attests as it
  runs every gate.

The packaged registry holds the obligations ETHOS owns. Every repository, ETHOS included, declares
its own gates in its profile or in the registry file its profile names. A repository's obligations
are therefore a function of the carriers it authors and the values it declares, the same under any
name, profile id, registry path, location or history. The ETHOS product that judges a repository
supplies the shared obligations, from the repository's own tree when that tree builds the product,
because the bytes it then binds are the bytes that tree executes.

## Alternatives Rejected

- **Repository-kind profiles:** rejected because a kind is a mixture of facts. Documentation,
  drawings, video, data and tools differ in which facts hold, and a kind would restate those facts
  and need a combined kind for every mixture.
- **Sinking by code similarity:** rejected because equal code can serve different meanings. A rule
  sinks when its meaning is the same for every repository, not when two copies look alike.
- **Starter templates:** rejected because a copied template becomes the repository's own text, so
  every repository owns the shared rule again and drifts from it.
- **An exemption that lets ETHOS judge itself by its own committed policy:** rejected because it
  made ETHOS's obligations depend on a path and a history rather than on its carriers.

## Consequences and Boundary

- ETHOS proves the shared quality floor with behavior and static evidence, as every repository
  does.
- The `pyproject.toml` distribution name, a declared carrier value, selects where shared data come
  from; no profile field or history check restates it.
- A rule that differs between repositories stays with each repository. A shared need that one owner
  cannot carry opens DR-0012's revisit; it never becomes a per-repository exception.
- Converting the shared floors that ETHOS still runs as its own sessions into providers, and
  retiring the copies, are later Changes under this record.

## Evidence and Revisit

- The `shared-quality-obligations` Change proposal and design record the two exceptions and the
  fact that replaced `product_source`.
- Its quality and repository-paradigm deltas state the obligations and their falsifiers. A symmetry
  regression varies the name, profile id, registry path, location and history of one repository and
  requires equal obligations.

Revisit when a governed repository shows a shared need whose rule differs between repositories, or
when selecting shared data needs more than the declared distribution. Retire this record when the
quality specification itself preserves these rejected alternatives and limits.
