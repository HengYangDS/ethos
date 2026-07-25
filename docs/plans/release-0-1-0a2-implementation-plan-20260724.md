---
subject: ethos:release-0-1-0a2-implementation-plan
role: plan
state: planned
relations:
  governed_by: docs/plans/release-0-1-0a2-design-20260724.md
---

# ETHOS 0.1.0a2 Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: execute this plan task-by-task
> with evidence checkpoints. This session uses inline execution because the
> user already authorized uninterrupted completion and valid-owner foreign
> Work Lanes must not be delegated or mutated.

**Goal:** Cut, prove, synchronize, observe, tag, and distribute the governed
ETHOS `0.1.0a2` prerelease without activating deferred package registries.

**Architecture:** One owned Work Lane changes every version carrier and the
changelog, then follows the canonical status-plan-prove-land-closeout loop.
After accepted closeout, branch synchronization, hosted observation, signed tag
publication, forge release assets, immutable evidence, and lane retirement are
performed as separately verified transitions.

**Tech Stack:** Python 3.14, uv, Hatchling, pytest, npm, Git SSH signing, ETHOS
CLI, GitHub CLI, GitLab CLI, repo-family governance.

## Global Constraints

- Python version is exactly `0.1.0a2`; npm version is exactly
  `0.1.0-alpha.2`; tag is exactly `v0.1.0a2`.
- `dev`, `main`, and `candidate/dev` must converge at one exact release HEAD.
- All remote pushes are explicit, non-force, and preceded by remote-head and
  dry-run checks.
- GitHub and GitLab observations are independent; canceled, missing, skipped,
  or failed required jobs are not success.
- PyPI, TestPyPI, npm registry, Homebrew, Docker/OCI, GitHub Marketplace, and
  GitLab Component publication remain deferred.
- Foreign valid-owner lanes are observe-only.

---

### Task 1: Update The Release Carriers

**Files:**

- Modify: `pyproject.toml`
- Modify: `pyproject.toml`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `package.json`
- Modify: `distributions/npm/package.json`
- Modify: `package-lock.json`
- Modify: `CHANGELOG.md`
- Modify: `tests/architecture/test_product_boundaries.py`
- Modify: `tests/unit/release/test_policy_attestation.py`

**Interfaces:**

- Consumes: the release design and the existing PEP 440/npm version mapping.
- Produces: one internally consistent release tree for `0.1.0a2`.

- [ ] Replace all active Python carrier values `0.1.0a1` with `0.1.0a2`.
- [ ] Replace all active npm carrier values `0.1.0-alpha.1` with
      `0.1.0-alpha.2`.
- [ ] Run `uv lock --offline` and verify that only workspace-version lock
      entries change.
- [ ] Run
      `npm install --package-lock-only --ignore-scripts --no-audit --no-fund`
      and verify that only the three npm version entries change.
- [ ] Add a new empty `Unreleased` section and date the existing release notes
      as `0.1.0a2 - 2026-07-24` without altering the historical `0.1.0a1`
      section.
- [ ] Update only tests that assert the current repository version; retain
      historical and pass-through fixture strings.
- [ ] Run:

  ```bash
  uv run --group dev pytest \
    tests/unit/release/test_policy_attestation.py \
    tests/architecture/test_product_boundaries.py -q
  uv run ethos quality release-policy --json
  uv run ethos quality sbom --json
  uv run ethos quality release-attestation --json
  npm ci --ignore-scripts
  npm run ethos -- --version
  npm run test:npm
  ```

- [ ] Require the Python CLI to print `0.1.0a2`, the npm tarball to be named
      `agentic-workflow-ethos-0.1.0-alpha.2.tgz`, and every command to exit 0.
- [ ] Commit the carrier change with subject
      `release: prepare 0.1.0a2`.

### Task 2: Compile And Execute Repository Proof

**Files:**

- Runtime evidence only under ignored `build/` paths.

**Interfaces:**

- Consumes: committed release carrier HEAD.
- Produces: HEAD-bound parity and full-proof evidence acceptable to land.

- [ ] Run `ethos status --json` and `ethos plan --changed --json` through the
      Work Lane runner with `ETHOS_ACTOR` bound to this lane holder.
- [ ] Run `ethos parity gaps --json`; if tracked parity is stale, execute and
      commit the generic shadow update in this Work Lane, then rerun all
      release checks.
- [ ] Run:

  ```bash
  tools/ci/scripts/run-local-ci.sh
  tools/ci/scripts/run-release-supply-chain.sh
  ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json
  ```

- [ ] Require all selected gates to pass and evidence to bind the unchanged
      Work Lane HEAD.
- [ ] Re-read `candidate/dev`; if it advanced, run the dry-run and apply forms
      of `ethos lane refresh-base`, resolve only this lane's replay, and repeat
      proof on the new HEAD.

### Task 3: Land And Close Out Accepted State

**Files:**

- Local Git refs and ETHOS proof-state projections only.

**Interfaces:**

- Consumes: proven Work Lane HEAD.
- Produces: local `candidate/dev`, `dev`, and `main` at the same release HEAD.

- [ ] Run dry-run `ethos land --expect-head "$(git rev-parse HEAD)" --json`.
- [ ] Run apply
      `ethos land --apply --authorize --expect-head "$(git rev-parse HEAD)" --json`.
- [ ] From the accepted root, run dry-run and apply accepted closeout with
      `ethos land --closeout`, `--expect-head`, `--authorize`, and `--apply`.
- [ ] Verify a clean accepted root and exact equality of `dev`, `main`, and
      `candidate/dev`.
- [ ] Run `ethos publish --probe-remote --json` without applying a push and
      retain the result as the pre-publication boundary.

### Task 4: Build The Final Distribution Bundle

**Files:**

- Generate: `build/artifacts/release-0.1.0a2/`
- Generate: `build/evidence/release/`

**Interfaces:**

- Consumes: final accepted release HEAD.
- Produces: checksummed Python, npm, SBOM, and attestation assets.

- [ ] Clean only the controlled release output directory.
- [ ] Build Python distributions with:

  ```bash
  uv build \
    --out-dir build/artifacts/release-0.1.0a2 \
    --clear --no-create-gitignore
  ```

- [ ] Build the npm tarball with
      `npm pack --workspace @agentic-workflow/ethos --pack-destination build/artifacts/release-0.1.0a2`.
- [ ] Run the local install smoke and verify imports and CLI version from the
      freshly built wheels.
- [ ] Save canonical JSON from `ethos quality sbom --json` and
      `ethos quality release-attestation --json` beside the artifacts.
- [ ] Generate `SHA256SUMS` with sorted base filenames and verify it with
      `shasum -a 256 -c SHA256SUMS`.
- [ ] Create `release-notes.md` from the `0.1.0a2` changelog section plus the
      explicit deferred-channel boundary.

### Task 5: Synchronize Both Forges And Observe Hosted CI

**Files:**

- Remote refs and external provider state only.

**Interfaces:**

- Consumes: exact accepted release HEAD and locally verified bundle.
- Produces: four synchronized remote branches and successful hosted evidence.

- [ ] Capture `git ls-remote` values for `dev`, `main`, and `v0.1.0a2` on both
      remotes and fail if the tag already exists or either branch is not an
      ancestor of the release HEAD.
- [ ] Run ordinary `git push --dry-run` for explicit `dev:dev` and `main:main`
      refspecs on `origin`, then on `github`.
- [ ] Run the same explicit pushes without `--dry-run`; never use force.
- [ ] Verify all four remote branch object IDs equal the release HEAD.
- [ ] Poll the GitHub Actions and GitLab pipeline APIs at bounded intervals
      until required branch pipelines for the release HEAD are terminal.
- [ ] Require successful required jobs for both `dev` and `main` on both
      providers. Investigate and repair any code failure through a new proven
      release HEAD; retry only infrastructure failures without weakening gates.
- [ ] Execute `tools/ci/scripts/run-hosted-provider-observation.sh` with
      `ETHOS_HOSTED_OBSERVATION_EXECUTE=1` and require current observations for
      the release HEAD.

### Task 6: Sign, Publish, And Verify The Release

**Files:**

- Create local and remote tag `v0.1.0a2`.
- Create GitHub and GitLab prerelease resources and assets.

**Interfaces:**

- Consumes: successful hosted branch observations and final bundle.
- Produces: signed immutable release identity and equal forge distributions.

- [ ] Create an SSH-signed annotated tag at the exact release HEAD:

  ```bash
  git tag -s -m "ETHOS 0.1.0a2" \
    v0.1.0a2 "$(git rev-parse HEAD)"
  git tag -v v0.1.0a2
  ```

- [ ] Dry-run then push `refs/tags/v0.1.0a2` to `origin` and `github` without
      force; verify the tag object and peeled commit on both remotes.
- [ ] Create the GitHub prerelease with `--verify-tag`, `--prerelease`,
      `--latest=false`, the checked release notes, and every bundle asset.
- [ ] Create the GitLab release against the existing tag with `--no-update`,
      the same release notes, and every bundle asset; do not use the generic
      package registry or component catalog.
- [ ] Query both forge APIs and compare tag, release name, prerelease state,
      asset filenames, asset byte sizes, and downloadable SHA-256 values.

### Task 7: Close Evidence And Retire The Work Lane

**Files:**

- Create one immutable record whose ID is computed with
  `record_id="$(date -u +%Y%m%dT%H%M%SZ)-release-0-1-0a2-closeout"` under the
  canonical repo-family evidence root.

**Interfaces:**

- Consumes: local proof, remote synchronization, hosted, tag, release, and
  artifact evidence.
- Produces: verified terminal closeout and no owned-lane residue.

- [ ] Run `record-admit` before creating the record.
- [ ] Copy only metadata, command JSON, release assets, and bounded logs; scan
      the record for secrets and workstation-private residue.
- [ ] Write `README.md`, `closeout.json`, `MANIFEST.json`, and `SHA256SUMS`;
      bind the release HEAD, tag object, artifact hashes, provider runs, release
      resources, and explicit deferred-channel limits.
- [ ] Run `record-verify`, then update the records index only after strict
      verification succeeds.
- [ ] Run `worktree-closeout-check` with the exact lane path, branch, holder,
      and expected release HEAD.
- [ ] Retire only `work/20260724-release-0-1-0a2` through the owner-bound landed
      path and verify branch ref, worktree path, and registration absence.
- [ ] Re-run accepted-root status, report, publish probe, hosted observation,
      release/tag API queries, record verification, repo-family audit, and safe
      housekeeping. Mark the long-running goal complete only if every acceptance
      fact in the release design still holds.
