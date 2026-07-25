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

The product topology is now declaration-first. The source of the path families,
required gap prefixes, lifecycle classes, generated filename rules, and product
adopter root exclusions is
`system/policies/generated-artifact-topology.toml`. The build declaration in
`pyproject.toml` projects it into installed wheels as
`ethos/data/generated_artifact_topology.toml`. Python loads the canonical
declaration in a checkout or the wheel resource elsewhere, then evaluates paths
through strict frozen contract models. It is not a second hand-written topology
table.

| Path family | Boundary | Generated output allowed? | Tracked? |
| --- | --- | --- | --- |
| `.config/ethos/` | Declarative config, policy, and adopter interface only. | No | Yes |
| `.cache/local-state/` and `.ethos/state/` | Host-local runtime state, leases, locks, executions, sessions. | Yes | No |
| `build/runtime/tool-cache/` | Tool runtime caches keyed by tool name. | Yes | No |
| `build/runtime/venv/` | Source-bound virtual environments for Work Lane runners. | Yes | No |
| `build/runtime/work/` | Provider emulator state and scratch working state. | Yes | No |
| `build/ethos/` | Machine proof, logs, reports, artifacts, and projections. | Yes | No |
| `build/evidence/` | Machine evidence bundles before review/promotion. | Yes | No |
| `build/artifacts/` | Local package and build artifacts, grouped by artifact kind. | Yes | No |
| `docs/evidence/`, `evidence/chronicle/`, `evidence/parity/` | Curated, dated, reviewable evidence summaries. | No raw output | Yes, after review |
| `docs/architecture/`, `docs/concepts/`, `docs/governance/`, `docs/reference/`, `docs/start/`, `docs/plans/`, `docs/research/`, `docs/history/`, `docs/decisions/` | Semantic docs truth and product documentation extensions; state is front matter, not generated output. | No | Yes, after review |
| `packages/`, `src/`, `tests/`, `rules/`, `system/` | Source, tests, rules, schemas, and contracts. | No | Yes, after review |

Evidence root topology is also declaration-first. The kernel `evidence/`
subroots, profile-curated `docs/evidence` mode, allowed root entrypoints, glob
patterns, and gap prefixes live in `system/policies/evidence-layout.toml`; its
wheel resource is projected by `pyproject.toml` as
`ethos/data/evidence_layout.toml`. `ethos.repository.evidence.topology`
scans filesystem facts and projects the read model from that declaration instead
of owning a second hand-written layout table.

Profile-mapped durable evidence roots preserve the same logical evidence
boundary without forcing every repository to copy the product repository's
physical `evidence/` kernel layout. When a governed repository declares
`[roots] durable_evidence = "docs/evidence"`, ETHOS treats that root as a
curated profile evidence home: reviewed, dated evidence subtrees such as
`docs/evidence/delivery/` or rollback-window summaries are allowed, while root
file clutter outside documented entrypoints remains blocked. Product-default
`evidence/` and other custom durable evidence roots keep the stricter kernel
layout with `claims/`, `chronicle/`, and `parity/` subroots. This keeps adopter
compatibility profile-driven instead of hardcoding adopter directories in the
ETHOS product.

Package metadata and lock files such as `package.json`, `package-lock.json`,
`pyproject.toml`, and `uv.lock` remain source/package authority. They are not
classified as generated drift merely because tools can update them.

Root `.coverage*`, `coverage.xml`, and `junit.xml` are tolerated only when they
are ignored, untracked local residue from coverage or pytest tooling. Tracked
instances of those files still fail the topology audit as root generated drift.
This keeps the gate from depending on test-gate cleanup order without turning
repo root into an output home.

Root cache homes such as `.import_linter_cache/`, `.import-linter-cache/`,
`.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.tox/`, `.nox/`,
`.uv-cache/`, and root `dist/` are denied even when ignored. They are local
residue, not semantic topology. Route them to `build/runtime/tool-cache/<tool>/`
or `build/artifacts/<kind>/`. New Work Lane Python environments belong under
`build/runtime/venv/` through `tools/ci/scripts/run-ethos-lane.sh`, not root
`.venv/`. Retired flat homes such as `build/cache/` and
`build/runtime/gitlab-ci-local/` are also denied; use
`build/runtime/tool-cache/<tool>/` and `build/runtime/work/gitlab-ci-local/`
instead.

## Lifecycle classes

The topology is a lifecycle model, not a prettier flat cache directory. Every
generated home answers four questions: can it be tracked, can it be promoted,
how is it regenerated, and how is it cleaned up?

| Lifecycle | Homes | Truth boundary | Cleanup / promotion rule |
| --- | --- | --- | --- |
| Runtime cache | `.cache/local-state/`, `.ethos/state/`, `build/runtime/tool-cache/`, `build/runtime/venv/`, `build/runtime/work/` | Disposable host-local or provider-local state. | Never promote. Delete or recreate from source commands. |
| Machine evidence | `build/evidence/`, `build/ethos/` | Generated, HEAD-bound command output before review. | Regenerate on HEAD movement. Promote only by explicit review or command into curated evidence. |
| Local artifact | `build/artifacts/` | Rebuildable package/build output. | Never treat as repository truth. Rebuild from package metadata or release commands. |
| Curated evidence | `docs/evidence/`, `evidence/chronicle/`, `evidence/parity/` | Reviewed, dated, tracked repository evidence. | Retire or supersede through tracked change; do not clean as cache. |

This is the reason `.import_linter_cache/` in repo root is wrong even when it is
ignored: it has a tool owner but no semantic lifecycle home. The right location
is `build/runtime/tool-cache/import-linter/`. Likewise, `build/cache/` is not
accepted as a generic dumping ground because it does not say whether the bytes
are cache, provider work, evidence, or package output.

## Promotion path

Machine evidence does not become repository truth by living under
`build/evidence/` or `build/ethos/`. Those homes are ignored, generated, and
HEAD-bound. A reviewer or explicit ETHOS command must summarize the bounded
claim, bind the command, scope, verifier, digest, and HEAD, and then promote the
reviewed record into `docs/evidence/`, `evidence/chronicle/`, or
`evidence/parity/`.

The path is therefore:

```text
runtime command -> build/evidence/<concern>/... or build/ethos/<concern>/...
  -> reviewed summary with command, scope, verifier, digest, HEAD
  -> curated tracked evidence under docs/evidence/, evidence/chronicle/, or evidence/parity/
```

Runtime caches under `.cache/local-state/`, `.ethos/state/`,
`build/runtime/tool-cache/`, `build/runtime/venv/`, or `build/runtime/work/`
are outside this path and
must never be promoted. Local artifacts under `build/artifacts/` are rebuilt
from source/package metadata rather than promoted as truth.

## Audit

```bash
ethos quality generated-artifacts --json
```

The audit reports the path router contract, lifecycle classes, entrypoint
routing, blocked generated drift, tracked files in generated-output homes, and
review-required paths. Its JSON contract includes `source_refs` so reviewers can
see which declaration supplied the topology. It is also a proof gate:

```bash
ethos prove --execute --gate generated-artifacts --expect-head <git-head> --json
```

## Entrypoint routing

The audit also checks the active producer entrypoints, not only files that
happen to exist after a run. Provider CI projections, reusable owner scripts,
package entrypoints, and tool configuration must route generated state before
the command writes it:

- `tools/ci/scripts/run-python-tests.sh` must call pytest with the explicit
  `.config/checks/pytest/pytest.ini` owner, route pytest cache to
  `build/runtime/tool-cache/pytest`, send coverage and JUnit machine evidence to
  `build/evidence/quality/tests/`, use an explicit scratch temp directory, and
  guard its generated coverage writer with a process-identity lock (PID plus
  start fingerprint). A dead recorded owner may be reclaimed; an unknown or
  live owner is never preempted and must fail after the bounded
  `ETHOS_COVERAGE_LOCK_WAIT_SECONDS` interval rather than leaving a later proof
  waiting forever.
- Ruff entrypoints must set `--cache-dir` or `RUFF_CACHE_DIR` to
  `build/runtime/tool-cache/ruff`.
- import-linter entrypoints must set `--cache-dir` or `IMPORT_LINTER_CACHE_DIR`
  to `build/runtime/tool-cache/import-linter`.
- Python package builds must use `uv build --out-dir build/artifacts/python` or
  an equivalent `build/artifacts/<kind>` route.
- `gitlab-ci-local` must use `--state-dir build/runtime/work/gitlab-ci-local`.

These checks prevent a cleanup-only failure mode: a gate should not merely
remove root residue after the fact; it should make the entrypoint incapable of
producing root or flat generated state during normal execution. Cleanup commands
may delete denied residue, but they do not authorize new producers.

## Adoption rollback

Adopters do not need product-owned `adopters/<name>`, `profiles/<name>`, or
fixture directories to use this contract. Adoption-side policy should be
declared in the adopter repository, for example under
`.config/ethos/generated-artifacts.toml`, and raw machine output should move to
ignored runtime/build homes such as `build/runtime/tool-cache/`,
`build/runtime/work/`, or `build/evidence/`. Rollback is likewise adopter-owned:
remove or relax the adopter declaration, move raw generated outputs back to an
ignored local/build home, and keep only curated evidence that has already been
reviewed and promoted.

`ethos fleet retirement-readiness --target <repo> --root <product> --json`
consumes this same audit before it can approve an embedded-backend retirement. A
retirement candidate must be clean under
`ethos quality generated-artifacts --root <repo> --json`; generated drift in repo
root, `.config/`, semantic docs truth, or source trees remains a blocking
adoption/rollback gap until moved to ignored runtime/build homes or promoted as
curated evidence.

## Documentation Kernel

ETHOS uses `docs/decisions/` for durable rulings and the shared docs kernel
defined in [Documentation Topology](docs-topology.md), so governed repositories
preserve decisions, evidence, reference vocabulary, and history without turning
product extension roots into mandatory truth lanes. ETHOS product extension
roots such as `docs/architecture/`, `docs/concepts/`, `docs/governance/`,
`docs/plans/`, `docs/research/`, and `docs/start/` remain semantic docs truth
homes; they are not generated-output homes and they are not required physical
lanes for every adopter.
