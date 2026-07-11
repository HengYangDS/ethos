---
subject: ethos:runtime-topology-convergence-20260711
role: plan
state: active
relations:
  implements: openspec/changes/archive/2026-07-11-runtime-topology-convergence-20260711
---

# Runtime Topology Convergence Plan

Status: implementation complete; local Work Lane closeout in progress.

Purpose: make every normal product Python execution checkout-bound and prevent
root `.venv` creation from product-owned executable entrypoints.

See also: [Generated Artifact Topology](../architecture/generated-artifact-topology.md)
and the [archived OpenSpec carrier](../../openspec/changes/archive/2026-07-11-runtime-topology-convergence-20260711/).

## Architecture

One shell bootstrap owns Python runtime environment binding:
`build/runtime/venv` is bound to the current checkout, while uv's content cache
is explicitly supplied by CI or defaults to host-local storage outside the
checkout. Owner scripts, local hooks, and declared runner payloads consume that
adapter; topology policy proves they cannot regress to root `.venv` or bare uv
execution. Existing root environments remain ignored migration residue until an
operator removes them deliberately.

## Constraints

- No normal tracked mutation outside this owned Work Lane.
- No mutation, deletion, or retirement of foreign Work Lane worktrees or root
  `.venv` directories. The current user-authorized integration decision permits
  this owned lane to update the four named provider projections as source files;
  it does not transfer, retire, or rewrite the overlapping foreign lane.
- Keep checkout environment, dependency cache, evidence, artifacts, and leases
  as distinct lifecycle classes.
- Preserve `ETHOS_PYTHON`, `PYTHON`, and CI `UV_CACHE_DIR` as bounded overrides;
  no root `.venv` default.
- Hosted CI success, local fallback CI, local candidate landing, accepted-root
  closeout, and remote publication remain separate claims.

## File Map

| Surface | Responsibility |
| --- | --- |
| `tools/ci/scripts/with-python-runtime.sh` | New sole runtime-binding adapter. |
| `tools/ci/scripts/run-*.sh`, `.githooks/*` | Consumers of the adapter; no root env fallback. |
| `.config/ci/templates/hosted/*`, `.github/workflows/ci.yml`, `.gitlab-ci.yml` | Provider templates and checked projections; all Python/uv producers invoke the adapter. |
| `system/policies/generated-artifact-topology.toml` + packaged mirror | Runtime lifecycle and entrypoint policy. |
| `packages/ethos/src/ethos/repository/policy/artifacts.py` | Executable-path audit. |
| `.config/checks/local-state/audit.toml`, `tools/ci/local_state_audit.py` | Migration-residue observation. |
| `packages/ethos/src/ethos/adapters/mutation/lanes.py` | Work Lane bootstrap contract. |
| `packages/ethos/src/ethos/repository/adoption/scaffold/template_files/` | Neutral adopter projection. |
| tests, docs, OpenSpec | Contract proof and explainability. |

## 1. Runtime bootstrap contract

- [x] Create `tools/ci/scripts/with-python-runtime.sh` as an executable, current-Git-root-bound adapter.
- [x] Add failing tests asserting two distinct worktrees receive distinct
  `UV_PROJECT_ENVIRONMENT` values and a supplied `UV_CACHE_DIR` wins.
- [x] Verify the new test fails because the adapter does not exist.
- [x] Implement exports: environment is `<repo>/build/runtime/venv`; cache is
  `ETHOS_UV_CACHE_DIR`, then `UV_CACHE_DIR`, then an OS user-cache default outside
  the checkout; create only the cache directory and let `uv` materialize the
  checkout environment lazily when it executes a uv-managed command or a missing
  default checkout interpreter is requested by a hook.
- [x] Add a `--` command boundary and execute the exact argument vector; reject
  empty command input with non-zero usage failure.
- [x] Run runtime bootstrap tests with the existing lane-bound test interpreter.

## 2. Product runner and owner-script migration

- [x] Add a failing hook/runner test requiring the adapter path and forbidding
  `.venv/bin/python` in active hook and owner-script execution lines.
- [x] Verify it fails against incumbent scripts.
- [x] Rewrite `run-ethos-lane.sh` as the public ETHOS command wrapper over the
  bootstrap, and update its payload to expose `environment_scope=checkout` and
  `cache_scope=host_or_ci`.
- [x] Migrate Python owner scripts to invoke the bootstrap around `uv run` or
  direct managed Python. Leave shell-only installers/scanners outside the
  contract unless they invoke Python/uv.
- [x] Migrate `pre-commit`, `pre-push`, and `reference-transaction` to use the
  checkout-managed interpreter with explicit source imports; preserve existing
  fail-closed/fail-open semantics. When that default interpreter is absent, the
  bootstrap MUST synchronize it with `uv run --group dev python`; explicitly
  injected interpreters retain caller-owned behavior. `pre-commit` MUST invoke
  Ruff through the bootstrap-bound dev group, so an existing runtime created by
  a non-dev command cannot leave the format guard without its required tool.
- [x] Run focused runner, hook, and owner-script topology tests.

## 3. Policy and audit promotion

- [x] Add failing topology tests for active root `.venv` fallback and bare
  `uv run` in executable producers, plus an allow case that calls the bootstrap.
- [x] Verify audit tests fail before policy implementation.
- [x] Extend both topology declarations and audit code so root `.venv` is a
  denied execution home, while a pre-existing ignored root environment is
  classified as migration residue rather than auto-cleanup debt.
- [x] Extend local-state audit output with an explicit migration-residue section
  that excludes third-party tree contents from flat ignored-state noise.
- [x] Update the Work Lane bootstrap response and focused test expectations.
- [x] Run policy, local-state, and command-contract tests.

## 4. Documentation and adoption projection

- [x] Update canonical runtime/topology docs to distinguish checkout venv from
  host/CI content cache and to state migration/rollback behavior.
- [x] Update adopter `.gitignore` and CI templates to model runtime state without
  treating root `.venv` as a normal launcher target.
- [x] Under the current user-authorized integration decision, route the named
  provider templates, checked projections, and local emulator wrappers through
  the bootstrap in this owned lane. Preserve template-to-projection byte parity;
  do not mutate or retire the overlapping foreign Work Lane.
- [x] Keep topology audit blocking for `.github/workflows/ci.yml`,
  `.gitlab-ci.yml`, `tools/ci/scripts/run-github-local-emulator.sh`, and
  `tools/ci/scripts/run-gitlab-local-emulator.sh` until all four invoke the
  bootstrap. Record the resulting overlap and later resolution in evidence; do
  not weaken the audit.
- [x] Add or update scoped doc and scaffold tests.

## 5. Proof and closeout

- [x] Mark OpenSpec tasks only after the implementation and test evidence exists.
- [x] Run OpenSpec strict validation and archive the complete carrier.
- [x] Run all focused tests and `ethos quality generated-artifacts --json` at a
  stable lane HEAD.
- [ ] Run final HEAD-bound proof and land only this lane to `candidate/dev` if it
  remains current and the recorded provider-projection dependency has been
  resolved by its owner.
- [ ] Re-run candidate proof and audited accepted-root closeout if candidate has
  no unrelated outstanding work; otherwise preserve this lane's landed state
  without advancing foreign work.
- [ ] Retire only this owned lane after accepted closeout. Run local publication
  readiness; remote GitLab remains deferred and unprobed.
