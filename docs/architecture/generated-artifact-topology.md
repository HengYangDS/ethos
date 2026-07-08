---
subject: ethos:generated-artifact-topology
role: reference
state: canonical
relations:
  canonical_for: generated artifact path ownership and drift detection
---

# Generated Artifact Topology

Status: canonical.

Purpose: define where generated outputs may exist, where curated evidence is
promoted, and which repository paths must never accumulate generated drift.

See also: [Command Plane](../reference/command-plane.md), [Local State](local-state.md),
[Provenance And Attestation](../governance/provenance-and-attestation.md), and
[Generated Artifact Topology Decision](../decisions/accepted/DR-0001-generated-artifact-topology-contract.md).

## Contract

Generated artifact placement is product governance, not housekeeping. ETHOS
routes each repository-relative path through one contract before it treats a
file as source, local state, generated output, or curated evidence.

| Path family | Boundary | Generated output allowed? | Tracked? |
| --- | --- | --- | --- |
| `.config/ethos/` | Declarative config, policy, and adopter interface only. | No | Yes |
| `.cache/local-state/` and `.ethos/state/` | Host-local runtime state, leases, locks, executions, sessions. | Yes | No |
| `build/ethos/` | Machine proof, logs, reports, artifacts, and projections. | Yes | No |
| `build/evidence/` | Machine evidence bundles before review/promotion. | Yes | No |
| `docs/evidence/`, `evidence/chronicle/`, `evidence/parity/` | Curated, dated, reviewable evidence summaries. | No raw output | Yes, after review |
| `docs/architecture/`, `docs/governance/`, `docs/reference/`, `docs/start/`, `docs/plans/`, `docs/history/`, `docs/decisions/` | Semantic docs truth; state is front matter, not generated output. | No | Yes, after review |
| `packages/`, `src/`, `tests/`, `rules/`, `system/` | Source, tests, rules, schemas, and contracts. | No | Yes, after review |

Package metadata and lock files such as `package.json`, `package-lock.json`,
`pyproject.toml`, and `uv.lock` remain source/package authority. They are not
classified as generated drift merely because tools can update them.

## Audit

```bash
ethos quality generated-artifacts --json
```

The audit reports the path router contract, blocked generated drift, tracked
files in generated-output homes, and review-required paths. It is also a proof
gate:

```bash
ethos prove --execute --gate generated-artifacts --expect-head <git-head> --json
```

## Adoption rollback

Adopters do not need product-owned `adopters/<name>`, `profiles/<name>`, or
fixture directories to use this contract. Adoption-side policy should be
declared in the adopter repository, for example under `.config/ethos/`, and raw
machine output should move to ignored runtime/build homes. Rollback is likewise
adopter-owned: remove or relax the adopter declaration, move raw generated
outputs back to an ignored local/build home, and keep only curated evidence that
has already been reviewed and promoted.

## Documentation Kernel

ETHOS uses `docs/decisions/` for durable rulings and the shared docs kernel
defined in [Documentation Topology](docs-topology.md), so governed repositories
preserve decisions, evidence, reference vocabulary, and history without turning
product extension roots into mandatory truth lanes.
