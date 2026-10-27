---
subject: docs:history
role: index
state: canonical
relations:
  canonical_for: historical documentation
---

# History Documentation

Status: canonical.

Purpose: hold retired rationale, archival logs, and migration history without
letting older vocabulary override current ETHOS contracts.

See also: [Documentation Root](../README.md), [Governance Docs](../governance/README.md),
[Reference Docs](../reference/README.md).

## Curated routes

History is an index over retained rationale and completed change records; it is
not a current-state ledger or another evidence store.

| Need                                         | Canonical record                                                                                                           |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Change carriers retained in the current tree | [OpenSpec archive](../../openspec/changes/archive/)                                                                        |
| Retired fixed-path documentation topology    | [Documentation Topology Contract, 2026-07-08](docs-topology-contract-20260708.md)                                          |
| Retired current-tree Change carriers         | Recover their exact Git revision as described below; current behavior belongs to [canonical specs](../../openspec/specs/). |

An archived Change is history, not a source of current requirements. The
accepted `352eed88ddcf1643945f6945363e1fab3fe1ba92` snapshot retains every
pre-September 2026 archived carrier. Once its current-tree copy retires,
inspect the selected object at that exact historical revision:

```bash
git ls-tree -r 352eed88ddcf1643945f6945363e1fab3fe1ba92 -- openspec/changes/archive/
git show 352eed88ddcf1643945f6945363e1fab3fe1ba92:openspec/changes/archive/2026-07-13-current-product-head-real-adopter-evidence/proposal.md
```

Verify the selected commit and path before using those bytes as historical
evidence. Current-tree retirement requires Git reachability and recovery
checks; this route gives old tasks and deltas no current authority.

## Historical Evidence Retrieval

The historical evidence tree is retained at source commit
`af350933c356c89dc9892652ebb943d478d464db`, tree
`a77f77462c487a7a9b7746f3e93b4bbdad8f51ce`. Retrieve exact bytes without
restoring a second workspace archive:

```bash
git ls-tree -r af350933c356c89dc9892652ebb943d478d464db -- evidence/
git show af350933c356c89dc9892652ebb943d478d464db:evidence/claims/current-head-real-adopter-evidence-20260714.toml
```

These are dated records, not the latest candidate or current proof. Historical
labels do not close unfinished obligations. Current product meaning belongs
to the product contract and official specifications; exact Git facts and
selected Attestations establish current implementation and proof.

## Terminal Plan Observations

The execution narrative formerly mixed into the terminal plan's current entry
remains in Git at `6182f688935e5ca0e83a18790953f0107b433fe9`, blob
`f2f7c6850ea75595ff2a873b79d69fd053af5ae0`:

```bash
git show 6182f688935e5ca0e83a18790953f0107b433fe9:docs/plans/terminal-governance-product-design.md
```

Use it for dated observations and discarded schedules, not current status.
Audit any still-valid obligation against the product contract, official OpenSpec
and terminal plan before treating it as transferred. Git recovery alone does
not prove semantic coverage. This reference adds no workspace history copy or
task ledger.

The earlier pre-campaign design remains at `10740ee14d79e4e5ab6c9b83bd91aa232e11f911`,
blob `fc37ffce043e66c22472e05516dcf158d93e77b7`:

```bash
git show 10740ee14d79e4e5ab6c9b83bd91aa232e11f911:docs/plans/terminal-governance-product-design.md
```

Its proposed workflow registry, capability metadata, hook envelope and physical
layout are audit inputs, not current product instructions. Later text does not
by itself establish that every distinct obligation was carried forward.

## Rewritten Commits

A history repair of `dev` on 2026-10-01 rewrote these previously cited commits;
each twin on `dev` has the identical tree.

| Cited commit                               | Twin on `dev`                              | Shared tree                                |
| ------------------------------------------ | ------------------------------------------ | ------------------------------------------ |
| `97196e96dd115f430e8dbb72af39f50b71d98a90` | `352eed88ddcf1643945f6945363e1fab3fe1ba92` | `8fac85e3e0da9bd26ec836fafea0f831f4f45ab7` |
| `06ea14f0ae9cfdf1e760ff8dc944b22c0b22361c` | `af350933c356c89dc9892652ebb943d478d464db` | `af1b9143888781df0be6063350ae5b645ea6b701` |
| `bac03b71c9771de27206385a70ae17e85dccb4f0` | `6182f688935e5ca0e83a18790953f0107b433fe9` | `7964ab3643c16d9066fed78a917f6aa4d8fa0f84` |
| `1137ffe46a3d7dda1a423026a6cfa5ceac78c07d` | `10740ee14d79e4e5ab6c9b83bd91aa232e11f911` | `8453aeb5c727c87782bc4aa331e13a4783b17e4f` |
| `81848f2fe50ef5ebea8f8e1dee75854a7be45c45` | `06bf5cc44405bb6572e3b33d1e798538bfe1d543` | `095ae97b117249031758817bfb0cbd6ba0ea9d06` |
| `d9a936edb49247d31e6dd4356ad00fd7d8c889cf` | `f99627cdcfe0a4e6dc8c4ee5b00aad7b79c59277` | `c1d155b35f0efe43a624d5d6684a0ddedf69fb5f` |
| `abc5ab1541834032cd27a79b18d89f9a49f49266` | `88186616714567768561e5447993e4ab5c999c04` | `4a6f8c46ada460b64aa6ff4b109714ab991511c2` |
| `e9bf7d27d5237ef1fb195b749ccdcbdcb3a8706d` | `d5e4f247e10a567b9af42f939bdf667201990dbc` | `29087dc5ff74905f7ffd38b983526f32c6ce82aa` |
| `2bfca40b80f8d998873a0f4edfeae055c4317e70` | `7de9b980fcd9b58e587955646eedef190c1a5673` | `a5eb74d1c64e3076b3adc0d5864802db87e63133` |
| `684823165b48c8d18ded89969fbfaeee15dd14f5` | `2e07e1dfc5e923458d93c91159fce607262bbc42` | `0fb96f678954a441e1108c3cf477261d88c9e494` |
| `7711c673648426ce8aace0e267340e02cb593591` | `eef582f11d0dcffd333eec62f66a988cf3123ae3` | `410d3447422c640b5f7e484014a23ac6202ae8cf` |
| `d5008a29e710660c1b231e958630bea7fe4fd8f7` | `3066334f03fb6b6ff6a2f3978174084459f8d559` | `2e40faa9cdd37fc93499f1164cf2673f635f80b2` |
| `c03e209118ba72120c58278996fab1a6043bc927` | `20192a13153d66c542f43834ca7ef39377ce19ea` | `1d2b0bcba0399fa4ebcfc0a3708d16f67aef8ca1` |
| `920eb0179bdd36903590da895beee0e5dc6394eb` | `4095d90be495a7ceb6815246c685f1b8fa7264f2` | `867e5d52984aa6c55eb1ddcb14194519c89bac56` |
