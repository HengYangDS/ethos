# Node Runtime Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development or
> superpowers:executing-plans task by task.

**Goal:** Prove the ETHOS npm launcher on Node 24.18.0 and 26.5.0 while keeping
Node 24.18.0 as the hosted packaging default.

**Architecture:** A TOML policy owns the exact versions and promotion trigger.
A reusable shell runner owns acceptance behavior. GitLab CI is a tested matrix
projection over those owners.

**Tech Stack:** TOML, Bash, GitLab CI YAML, pytest architecture contracts,
OpenSpec 1.6.

## Global Constraints

- Do not modify host-managed IDE or application Node runtimes.
- Do not change the Node 24.18.0 packaging default in this change.
- Do not change packageManager = npm@11.12.1 in this change.
- All tracked writes occur in the admitted Work Lane.
- Use failing contract tests before implementation.

---

### Task 1: Add failing compatibility ownership contracts

**Files:**
- Modify: tests/architecture/test_release_assets.py
- Modify: tests/architecture/test_ci_provider_projections.py

**Produces:** Contracts for the policy owner, reusable runner, exact version
set, GitLab matrix, and unchanged Node 24 packaging default.

- [ ] Add assertions that parse .config/checks/node/runtime.toml and require
      default = 24.18.0 plus compatibility versions 24.18.0 and 26.5.0.
- [ ] Require tools/ci/scripts/run-node-compatibility.sh from the GitLab npm
      verification job and require the exact two-version matrix.
- [ ] Run the focused pytest command for both architecture files.
- [ ] Confirm failure because the new owner and runner do not exist.

### Task 2: Add the policy owner and reusable runner

**Files:**
- Create: .config/checks/node/runtime.toml
- Create: tools/ci/scripts/run-node-compatibility.sh
- Modify: system/tools.toml

**Produces:** One exact compatibility policy and one executable acceptance
surface.

- [ ] Define Node 24.18.0 as default_version, Node 26.5.0 as
      next_default_candidate, both versions as compatibility_versions, and
      2026-10-28 as review_not_before.
- [ ] Implement a runner that reads the TOML policy with Python tomllib,
      rejects a runtime/version mismatch, and runs npm ci --ignore-scripts,
      npm run ethos -- --version, and npm run test:npm.
- [ ] Register the policy and runner in system/tools.toml.
- [ ] Run the focused tests and confirm only the CI projection remains red.

### Task 3: Project the compatibility matrix into hosted CI

**Files:**
- Modify: .gitlab-ci.yml

**Produces:** Two GitLab verification instances, one for each exact Node
release, while the packaging job keeps the installer default.

- [ ] Add parallel.matrix with Node 24.18.0 and 26.5.0 to ethos:npm.
- [ ] Replace inline npm acceptance commands with the reusable runner.
- [ ] Leave ethos:npm-package on the installer default.
- [ ] Run the focused architecture tests and confirm green.

### Task 4: Record product intent and OpenSpec delta

**Files:**
- Modify: docs/architecture/distribution.md
- Create: openspec/changes/node-runtime-compatibility-20260716/.openspec.yaml
- Create: openspec/changes/node-runtime-compatibility-20260716/proposal.md
- Create: openspec/changes/node-runtime-compatibility-20260716/design.md
- Create: openspec/changes/node-runtime-compatibility-20260716/tasks.md
- Create: openspec/changes/node-runtime-compatibility-20260716/specs/quality/spec.md

**Produces:** Provider-neutral compatibility and promotion boundaries.

- [ ] Document workstation, project, hosted, and managed-runtime ownership.
- [ ] State that 2026-10-28 is a review trigger rather than automatic
      promotion.
- [ ] Run strict OpenSpec validation for the change.

### Task 5: Execute runtime and repository proof

**Files:** No additional product source.

**Produces:** Local version-specific evidence and HEAD-bound repository proof.

- [ ] Run the compatibility runner under isolated Linux Node 24.18.0.
- [ ] Run the compatibility runner under isolated Linux Node 26.5.0.
- [ ] Run focused architecture tests, config lint, shell lint, and quality
      audit.
- [ ] Commit the stable change.
- [ ] Run ethos plan --changed --json.
- [ ] Run parity checks required by the compiled plan.
- [ ] Run HEAD-bound ethos prove --execute.
- [ ] Land locally only when every required gap is closed; do not push.
