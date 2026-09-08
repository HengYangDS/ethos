---
subject: ethos:generated-artifact-topology
role: reference
state: canonical
relations:
  canonical_for: generated artifact path ownership and drift detection
---

# Generated Artifact Topology

Status: canonical.

Purpose: define generated-output ownership, lifecycle and the boundary between
rebuildable material, persistent proof and maintained source.

See also: [Command Plane](../reference/command-plane.md), [Local State](local-state.md),
and [Provenance And Attestation](../governance/provenance-and-attestation.md).

## Contract

Generated artifact placement is product governance, not housekeeping. ETHOS
routes each repository-relative path through one contract before it treats a
file as source, local state or generated output.

The product topology is now declaration-first. The source of the path families,
required gap prefixes, lifecycle classes, generated filename rules, and product
adopter root exclusions is
`system/policies/generated-artifact-topology.toml`. The build declaration in
`pyproject.toml` projects it into installed wheels as
`ethos/data/generated_artifact_topology.toml`. Python loads the canonical
declaration in a checkout or the wheel resource elsewhere, then evaluates paths
through strict frozen contract models. It is not a second hand-written topology
table.

| Path family                                                                                                                                                       | Boundary                                                                                               | Generated output allowed? | Tracked?          |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------- | ----------------- |
| `.config/ethos/`                                                                                                                                                  | Declarative config, policy, and adopter interface only.                                                | No                        | Yes               |
| `<git-common-dir>/ethos/`                                                                                                                                         | ETHOS leases, runtime artifacts, and transaction state shared by worktrees.                            | Yes                       | Outside checkout  |
| `.cache/local-state/`                                                                                                                                             | Repository-native host-local state.                                                                    | Yes                       | No                |
| `build/runtime/tool-cache/`                                                                                                                                       | Tool runtime caches keyed by tool name.                                                                | Yes                       | No                |
| `.venv/`                                                                                                                                                          | Repository-local Python environment selected by `uv.lock`.                                             | Yes                       | No                |
| `build/runtime/work/`                                                                                                                                             | Provider emulator state and scratch working state.                                                     | Yes                       | No                |
| `build/ethos/`                                                                                                                                                    | Machine proof, logs, reports, artifacts, and projections.                                              | Yes                       | No                |
| `build/evidence/`                                                                                                                                                 | Machine evidence bundles before review/promotion.                                                      | Yes                       | No                |
| `build/artifacts/`                                                                                                                                                | Local package and build artifacts, grouped by artifact kind.                                           | Yes                       | No                |
| `docs/architecture/`, `docs/concepts/`, `docs/decisions/`, `docs/governance/`, `docs/reference/`, `docs/guides/`, `docs/plans/`, `docs/research/`, `docs/history/` | Semantic docs truth and product documentation extensions; state is front matter, not generated output. | No                        | Yes, after review |
| `packages/`, `src/`, `tests/`, `rules/`, `system/`                                                                                                                | Source, tests, rules, schemas, and contracts.                                                          | No                        | Yes, after review |

Current proof belongs to the independent Git-native Attestation set selected
by `refs/ethos/attestations-set`, not to a workspace directory. Generated-output
placement does not establish proof currentness; the selected Attestation's
predicate and exact bindings do. Historical records remain in Git rather than
requiring a duplicate root or a profile evidence-directory declaration.

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
the root `.venv/` through `uv run --frozen --offline ethos`. Retired flat
homes such as `build/cache/` and
`build/runtime/gitlab-ci-local/` are also denied; use
`build/runtime/tool-cache/<tool>/` and `build/runtime/work/gitlab-ci-local/`
instead.

## Lifecycle classes

The topology is a lifecycle model, not a prettier flat cache directory. Every
generated home answers four questions: can it be tracked, can it be promoted,
how is it regenerated, and how is it cleaned up?

| Lifecycle        | Homes                                                                                                          | Truth boundary                                        | Cleanup / promotion rule                                                                       |
| ---------------- | -------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Runtime cache    | `<git-common-dir>/ethos/`, `.cache/local-state/`, `.venv/`, `build/runtime/tool-cache/`, `build/runtime/work/` | Disposable host-local or provider-local state.        | Never promote. Delete or recreate from source commands.                                        |
| Machine evidence | `build/evidence/`, `build/ethos/`                                                                              | Generated, HEAD-bound command output before review.   | Regenerate on HEAD movement. Record a bounded Attestation through the existing command owner. |
| Local artifact   | `build/artifacts/`                                                                                             | Rebuildable package/build output.                     | Never treat as repository truth. Rebuild from package metadata or release commands.            |

This is the reason `.import_linter_cache/` in repo root is wrong even when it is
ignored: it has a tool owner but no semantic lifecycle home. The right location
is `build/runtime/tool-cache/import-linter/`. Likewise, `build/cache/` is not
accepted as a generic dumping ground because it does not say whether the bytes
are cache, provider work, evidence, or package output.

## Proof Recording

Machine output does not become proof by living under `build/evidence/` or
`build/ethos/`. An explicit ETHOS command validates its bounded result and
records a canonical Attestation in `refs/ethos/attestations-set`. Readers select
the required predicate and exact bindings, not a directory or summary.

```text
bounded command -> generated output and post-effect observations
  -> validated Attestation selected by refs/ethos/attestations-set
```

A useful explanation belongs with its existing semantic documentation owner.
Runtime caches remain disposable; package artifacts remain rebuildable from
source and locks. Proof records and required supporting objects retain their
own reachability and retention lifecycle independently of workspace cleanup.

## Audit

```bash
ethos prove --gate generated-artifacts --json
```

The audit is the sole owner of generated and local-state topology. It reports the
path router contract, lifecycle classes, entrypoint routing, blocked generated
drift, tracked files in generated-output homes, and review-required paths. Its
JSON contract includes `source_refs` so reviewers can see which declaration
supplied the topology. It is also a proof gate:

```bash
ethos prove --execute --gate generated-artifacts --expect-head <git-head> --json
```

## Entrypoint routing

The audit also checks the active producer entrypoints, not only files that
happen to exist after a run. Provider CI projections, reusable owner scripts,
package entrypoints, and tool configuration must route generated state before
the command writes it:

- `noxfile.py` and `tools/ci/python_test_gate.py` must call pytest with the explicit
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
- Python package builds must use the repository `nox -s build` owner, which
  routes Hatchling output to `build/artifacts/python`.
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
ignored local/build home, and retain the selected Attestations and supporting
objects still required by current consumers.

`ethos prove --gate generated-artifacts --root <repo> --json` consumes this
same audit before it can support an execution-substrate transition. A transition
candidate must be clean under that proof gate; generated drift in repo
root, `.config/`, semantic docs truth, or source trees remains a blocking
adoption/rollback gap until its exact generated output is routed to an admitted
home and any required proof has been recorded through the current owner.

## Documentation Kernel

The portable documentation contract is [Docs Registry](../governance/docs-registry.md):
it governs metadata and discoverability, while physical subject roots remain
repository-native. ETHOS product roots such as `docs/architecture/`,
`docs/concepts/`, `docs/decisions/`, `docs/governance/`, `docs/plans/`,
`docs/research/`, and `docs/guides/` are semantic documentation homes. They are
not generated-output homes and are not imposed on adopters.
