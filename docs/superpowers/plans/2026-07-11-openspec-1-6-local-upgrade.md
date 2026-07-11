# OpenSpec 1.6 Local Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the local OpenSpec host, dual Codex projections, and the three canonical repositories onto the official `1.6.0` release with reproducible pins and verified 1.6 workflow compatibility.

**Architecture:** The host remains the shared distribution point for OpenSpec configuration and Codex prompts. Repository-owned pins, generated vendor artifacts, and runtime contracts remain in their respective repositories and are changed only in owned Work Lanes. Each repository delivers a self-contained commit and proof result; no active foreign worktree, candidate checkout, or historical evidence is edited.

**Tech Stack:** OpenSpec `1.6.0`, Node.js/npm/npx, Codex and JetBrains Codex homes, Python 3.12, uv, Pixi, Docker Compose, pytest, Git worktrees/ETHOS Work Lanes.

## Global Constraints

- Repository-owned OpenSpec tool supply uses the exact literal `1.6.0`.
- The host launcher at `/Users/yheng/.local/bin/openspec` remains the existing floating host-managed updater; its effective version must be verified as `1.6.0`.
- OpenSpec global config is `profile: core`, `delivery: both`, with `propose`, `explore`, `apply`, `update`, `sync`, and `archive`.
- Do not edit candidate checkouts, foreign Work Lanes, preserved worktrees, archived OpenSpec records, historical evidence, or unrelated user changes.
- Run `ETHOS_ACTOR=agent:codex:thread:019f4fbf-b0b7-7e22-85ea-9c546512972e` for ETHOS write-capable commands in the owned ETHOS Work Lane.
- Never manually edit official-generated `openspec-*` skill files; regenerate them with the official CLI.
- Local acceptance and remote publication are separate states. This plan does not publish branches remotely.

______________________________________________________________________

## File Structure

| Scope           | Files                                                                                                                                                                                          | Responsibility                                                           |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Host            | `/Users/yheng/.config/openspec/config.json`, `/Users/yheng/.codex/prompts/opsx-*.md`, `/Users/yheng/Library/Caches/JetBrains/PyCharm2026.1/aia/codex/prompts/opsx-*.md`                        | Shared workflow selection and current OPSX commands.                     |
| ETHOS           | `packages/ethos/src/ethos/adapters/openspec/cli.py`, `tools/ci/scripts/bootstrap-python.sh`, `packages/ethos/src/ethos/repository/adoption/scaffold/template_files/ci/gitlab.yml.j2`           | Exact official CLI fallback and CI/adopter supply pins.                  |
| ETHOS tests     | `tests/unit/cli/test_contracts.py`, `tests/unit/product/test_openspec_edges.py`, `tests/architecture/test_ci_provider_projections.py`                                                          | Pin and provider-projection contracts.                                   |
| alphasim        | `pyproject.toml`, `justfile`, `.codex/skills/openspec-*/SKILL.md`, `.claude/skills/openspec-*/SKILL.md`, `docs/current/development/workflow/agentic-sdd-workflow.md`                           | Exact CLI pin, official generated skills, and current operator guidance. |
| alphasim tests  | `tests/architecture/development/test_docs_workflow_architecture.py`                                                                                                                            | Exact pins and all six core generated skills.                            |
| di-effect       | `tools/agentic/Dockerfile`, `.config/env/tools/.env.tools.example`, `tools/agentic/README.md`, `packages/di-effect-tooling/src/di_effect_tooling/repo/runtime/checks/cli/agentic_toolchain.py` | Docker/env supply pin and fail-closed runtime contract.                  |
| di-effect tests | `tests/unit/di_effect_tooling/repo/runtime/checks/cli/test_agentic_toolchain.py`                                                                                                               | Current-repository assertion for the OpenSpec 1.6 toolchain contract.    |

## Task 1: Upgrade the shared OpenSpec profile for subsequent Codex projections

**Files:**

- Modify: `/Users/yheng/.config/openspec/config.json`
- Create/update: `/Users/yheng/.codex/prompts/opsx-{propose,explore,apply,update,sync,archive}.md`
- Create/update: `/Users/yheng/Library/Caches/JetBrains/PyCharm2026.1/aia/codex/prompts/opsx-{propose,explore,apply,update,sync,archive}.md`
- Use as generation root: `/Users/yheng/projects/alphasim-dmgr-fix-b3`

**Interfaces:**

- Consumes: official `openspec config profile core`, `openspec config set delivery both`, and `openspec update --force`.

- Produces: a global core workflow profile and two Codex prompt projections used by every repository in later tasks.

- [ ] **Step 1: Capture reversible host state and verify the expected pre-upgrade mismatch**

Run:

```bash
stamp="$(date +%Y%m%d-%H%M%S)"
backup="/Users/yheng/.config/openspec/backups/${stamp}-before-1.6"
mkdir -p "$backup"
cp -p /Users/yheng/.config/openspec/config.json "$backup/config.json"
cp -a /Users/yheng/.codex/prompts "$backup/codex-prompts" 2>/dev/null || true
cp -a /Users/yheng/Library/Caches/JetBrains/PyCharm2026.1/aia/codex/prompts "$backup/pycharm-codex-prompts" 2>/dev/null || true
openspec --version
openspec config list
```

Expected: `openspec --version` prints `1.6.0`; config reports the stale custom profile with `delivery: skills` and no `update` workflow.

- [ ] **Step 2: Apply the official core profile and both delivery modes**

Run:

```bash
openspec config profile core
openspec config set delivery both
openspec config list
```

Expected config fields:

```yaml
profile: core
delivery: both
workflows:
  - propose
  - explore
  - apply
  - update
  - sync
  - archive
```

- [ ] **Step 3: Verify the host profile before a repository generates projections**

Run:

```bash
openspec config get profile
openspec config get delivery
openspec --version
```

Expected: commands exit `0`; profile is `core`, delivery is `both`, and the effective CLI version is `1.6.0`. Task 3 generates the tracked skills and dual-Codex prompt projections after its alphasim Work Lane exists.

## Task 2: Pin ETHOS-owned OpenSpec supply and prove official fallback behavior

**Files:**

- Modify: `/Users/yheng/projects/ethos-worktrees/openspec-1-6-local-upgrade-20260711/packages/ethos/src/ethos/adapters/openspec/cli.py:9-34`
- Modify: `/Users/yheng/projects/ethos-worktrees/openspec-1-6-local-upgrade-20260711/tools/ci/scripts/bootstrap-python.sh:15`
- Modify: `/Users/yheng/projects/ethos-worktrees/openspec-1-6-local-upgrade-20260711/packages/ethos/src/ethos/repository/adoption/scaffold/template_files/ci/gitlab.yml.j2:9`
- Modify: `/Users/yheng/projects/ethos-worktrees/openspec-1-6-local-upgrade-20260711/tests/unit/cli/test_contracts.py:629,638-642`
- Modify: `/Users/yheng/projects/ethos-worktrees/openspec-1-6-local-upgrade-20260711/tests/unit/product/test_openspec_edges.py:351-364`
- Modify: `/Users/yheng/projects/ethos-worktrees/openspec-1-6-local-upgrade-20260711/tests/architecture/test_ci_provider_projections.py`

**Interfaces:**

- Consumes: Task 1's verified host CLI and `OFFICIAL_NPX_PACKAGE` used by `openspec_base_command()`.

- Produces: deterministic ETHOS CI/scaffold fallback invocation `npx --yes @fission-ai/openspec@1.6.0`, while preserving cache and explicit-binary precedence.

- [ ] **Step 1: Write failing pin and CI-projection assertions**

Add to `tests/unit/product/test_openspec_edges.py` a fallback-path test that disables the cache and `openspec` executable, then expects:

```python
assert openspec_cli.openspec_base_command() == (
    "npx",
    "--yes",
    "@fission-ai/openspec@1.6.0",
)
```

Update the `official_cli["package"]` assertions in `tests/unit/cli/test_contracts.py` to `"@fission-ai/openspec@1.6.0"`. Add an architecture test that reads the two CI owner files and asserts both literals:

```python
assert 'npx --yes @fission-ai/openspec@1.6.0 "$@"' in bootstrap
assert "npm install -g @fission-ai/openspec@1.6.0" in adopter_gitlab_template
```

- [ ] **Step 2: Run the focused tests to prove the current implementation is still stale**

Run:

```bash
cd /Users/yheng/projects/ethos-worktrees/openspec-1-6-local-upgrade-20260711
uv run --package ethos pytest \
  tests/unit/product/test_openspec_edges.py \
  tests/unit/cli/test_contracts.py \
  tests/architecture/test_ci_provider_projections.py -q
```

Expected: failure because the package and CI surfaces still use unversioned OpenSpec.

- [ ] **Step 3: Make the minimal source and CI changes**

Change the adapter constant and the two supply surfaces to these exact values:

```python
OFFICIAL_NPX_PACKAGE = "@fission-ai/openspec@1.6.0"
```

```bash
printf '%s\n' '#!/usr/bin/env bash' 'exec npx --yes @fission-ai/openspec@1.6.0 "$@"' > /usr/local/bin/openspec
```

```yaml
- npm install -g @fission-ai/openspec@1.6.0
```

Do not alter the explicit `ETHOS_OPENSPEC_BIN`, cached-official-cli, or PATH precedence in `openspec_base_command()`.

- [ ] **Step 4: Re-run focused tests and official strict validation**

Run:

```bash
cd /Users/yheng/projects/ethos-worktrees/openspec-1-6-local-upgrade-20260711
uv run --package ethos pytest \
  tests/unit/product/test_openspec_edges.py \
  tests/unit/cli/test_contracts.py \
  tests/architecture/test_ci_provider_projections.py -q
openspec validate --all --strict --json
```

Expected: pytest exits `0` and OpenSpec reports zero failed items.

- [ ] **Step 5: Commit the ETHOS lane change after write admission**

Run:

```bash
cd /Users/yheng/projects/ethos-worktrees/openspec-1-6-local-upgrade-20260711
ETHOS_ACTOR=agent:codex:thread:019f4fbf-b0b7-7e22-85ea-9c546512972e \
  uv run --package ethos ethos lane prewrite \
  packages/ethos/src/ethos/adapters/openspec/cli.py \
  tools/ci/scripts/bootstrap-python.sh \
  packages/ethos/src/ethos/repository/adoption/scaffold/template_files/ci/gitlab.yml.j2 \
  tests/unit/cli/test_contracts.py \
  tests/unit/product/test_openspec_edges.py \
  tests/architecture/test_ci_provider_projections.py \
  --editor-root "$PWD" --require-editor-root --json
git add packages/ethos/src/ethos/adapters/openspec/cli.py \
  tools/ci/scripts/bootstrap-python.sh \
  packages/ethos/src/ethos/repository/adoption/scaffold/template_files/ci/gitlab.yml.j2 \
  tests/unit/cli/test_contracts.py \
  tests/unit/product/test_openspec_edges.py \
  tests/architecture/test_ci_provider_projections.py
ETHOS_ACTOR=agent:codex:thread:019f4fbf-b0b7-7e22-85ea-9c546512972e \
  git commit -m "build: pin ETHOS OpenSpec to 1.6.0"
```

Expected: one isolated ETHOS commit with no historical evidence edits.

## Task 3: Regenerate alphasim official skills and align the current workflow contract

**Files:**

- Modify: `/Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6/pyproject.toml:163-164`
- Modify: `/Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6/justfile:168-172`
- Regenerate: `/Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6/.codex/skills/openspec-*/SKILL.md`
- Regenerate: `/Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6/.claude/skills/openspec-*/SKILL.md`
- Modify: `/Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6/docs/current/development/workflow/agentic-sdd-workflow.md:820-854`
- Modify: `/Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6/tests/architecture/development/test_docs_workflow_architecture.py:16-58`

**Interfaces:**

- Consumes: Task 1 global `core`/`both` configuration and the exact npm package version.

- Produces: `pixi run openspec`, `just openspec`, Codex, and Claude all use the six-workflow official OpenSpec 1.6 projection.

- [ ] **Step 1: Create the alphasim Work Lane from its clean accepted root**

Run from `/Users/yheng/projects/alphasim-dmgr-fix-b3`:

```bash
pixi run ethos lane start openspec-1-6 \
  --path /Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6 \
  --holder-ref agent:codex:thread:019f4fbf-b0b7-7e22-85ea-9c546512972e \
  --apply --json
```

Expected: an owned `work/openspec-1-6` linked worktree. Do not edit the primary checkout, which contains untracked `.agents/skills/openspec-*` residue.

- [ ] **Step 2: Write failing architecture assertions for exact pins and the new generated workflow**

Extend `test_native_openspec_workflow_is_officially_integrated()` with:

```python
expected_openspec_skills = {
    "openspec-apply-change",
    "openspec-archive-change",
    "openspec-explore",
    "openspec-propose",
    "openspec-sync-specs",
    "openspec-update-change",
}
tasks = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
    "tool"
]["pixi"]["tasks"]
assert tasks["openspec"] == "npx --yes @fission-ai/openspec@1.6.0"
assert tasks["openspec-check"].startswith("npx --yes @fission-ai/openspec@1.6.0")
assert 'npx --yes @fission-ai/openspec@1.6.0 "$@"' in (
    PROJECT_ROOT / "justfile"
).read_text(encoding="utf-8")
assert "/opsx:update" in workflow
for root in (PROJECT_ROOT / ".codex" / "skills", PROJECT_ROOT / ".claude" / "skills"):
    assert 'generatedBy: "1.6.0"' in (
        root / "openspec-update-change" / "SKILL.md"
    ).read_text(encoding="utf-8")
```

- [ ] **Step 3: Run the focused architecture test and confirm it fails before regeneration**

Run:

```bash
cd /Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6
pixi run pytest \
  tests/architecture/development/test_docs_workflow_architecture.py::test_native_openspec_workflow_is_officially_integrated -q
```

Expected: failure because current pins are `1.5.0`, generated skills are `1.4.1`, and `openspec-update-change` is absent.

- [ ] **Step 4: Update exact pins and regenerate instead of editing generated skills**

Replace both `1.5.0` literals in `pyproject.toml` and both literals in `justfile` with `1.6.0`. In the current OpenSpec section of `agentic-sdd-workflow.md`, add this operator rule:

```markdown
Use `/opsx:update <change>` only to reconcile an active change's proposal, design,
tasks, and delta artifacts; it must not edit implementation code. Continue with
`/opsx:apply` only after the revised plan is confirmed.
```

Then generate vendor artifacts:

```bash
cd /Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6
CODEX_HOME=/Users/yheng/.codex openspec update --force
CODEX_HOME=/Users/yheng/Library/Caches/JetBrains/PyCharm2026.1/aia/codex \
  openspec update --force
```

Expected generated artifacts: six `openspec-*` skill directories under both `.codex/skills/` and `.claude/skills/`, including `openspec-update-change`, all with `generatedBy: "1.6.0"`; both Codex homes contain six current core `opsx-*.md` prompts. Do not restart or terminate PyCharm/Codex as part of this task.

- [ ] **Step 5: Run the focused architecture and native gates**

Run:

```bash
cd /Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6
pixi run pytest \
  tests/architecture/development/test_docs_workflow_architecture.py::test_native_openspec_workflow_is_officially_integrated -q
pixi run openspec-check
pixi run ethos quality projection-drift --json
```

Expected: all commands exit `0`; OpenSpec validates before ETHOS projection checks.

- [ ] **Step 6: Commit the isolated alphasim change**

Run:

```bash
cd /Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6
git add pyproject.toml justfile .codex/skills .claude/skills \
  docs/current/development/workflow/agentic-sdd-workflow.md \
  tests/architecture/development/test_docs_workflow_architecture.py
git diff --cached --check
git commit -m "build: upgrade OpenSpec workflow to 1.6.0"
```

Expected: one Work Lane commit; no `.agents/skills/openspec-*` file is added.

## Task 4: Make the di-effect Docker/env contract reject stale OpenSpec versions

**Files:**

- Modify: `/Users/yheng/projects/di-effect-task-openspec-1-6/tools/agentic/Dockerfile:4`
- Modify: `/Users/yheng/projects/di-effect-task-openspec-1-6/.config/env/tools/.env.tools.example:70`
- Modify: `/Users/yheng/projects/di-effect-task-openspec-1-6/tools/agentic/README.md:47-51`
- Modify: `/Users/yheng/projects/di-effect-task-openspec-1-6/packages/di-effect-tooling/src/di_effect_tooling/repo/runtime/checks/cli/agentic_toolchain.py:27-67,123-180`
- Create: `/Users/yheng/projects/di-effect-task-openspec-1-6/tests/unit/di_effect_tooling/repo/runtime/checks/cli/test_agentic_toolchain.py`

**Interfaces:**

- Consumes: `DI_EFFECT_AGENTIC_OPENSPEC_VERSION` from the tracked example environment and `OPENSPEC_VERSION` passed by Docker Compose.

- Produces: a runtime checker that reports an error if either tracked supply surface drifts from `1.6.0`.

- [ ] **Step 1: Create an isolated di-effect task worktree**

Run from `/Users/yheng/projects/di-effect`:

```bash
git worktree add \
  /Users/yheng/projects/di-effect-task-openspec-1-6 \
  -b task/openspec-1-6 dev
```

Expected: a linked `task/openspec-1-6` worktree based on `dev`. Preserve the two unrelated modified source files in the primary checkout.

- [ ] **Step 2: Write a failing runtime-contract test**

Create `tests/unit/di_effect_tooling/repo/runtime/checks/cli/test_agentic_toolchain.py` with a repository-file assertion and a stale-value probe:

```python
from pathlib import Path

import di_effect_tooling.repo.runtime.checks.cli.agentic_toolchain as agentic_toolchain
from di_effect_tooling.repo.runtime.paths.root import resolve_repo_root


def test_agentic_openspec_supply_is_exactly_pinned_to_1_6_0() -> None:
    root = resolve_repo_root(__file__)
    assert agentic_toolchain.REQUIRED_OPENSPEC_VERSION == "1.6.0"
    assert "ARG OPENSPEC_VERSION=1.6.0" in (
        root / "tools/agentic/Dockerfile"
    ).read_text(encoding="utf-8")
    assert "DI_EFFECT_AGENTIC_OPENSPEC_VERSION=1.6.0" in (
        root / ".config/env/tools/.env.tools.example"
    ).read_text(encoding="utf-8")
    assert agentic_toolchain._collect_issues(root) == []
```

Add this complete stale-value test below the repository-file assertion:

```python
def test_agentic_toolchain_reports_stale_openspec_environment_pin(
    tmp_path: Path,
) -> None:
    dockerfile = tmp_path / "tools/agentic/Dockerfile"
    dockerfile.parent.mkdir(parents=True)
    dockerfile.write_text(
        "FROM python:3.12-slim AS agentic-base\n"
        "FROM agentic-base AS agentic-openspec\n"
        "ARG OPENSPEC_VERSION=1.6.0\n"
        'RUN npm install --global "@fission-ai/openspec@${OPENSPEC_VERSION}"\n',
        encoding="utf-8",
    )
    compose = tmp_path / "tools/agentic/docker-compose.agentic-tools.yml"
    compose.write_text(
        "services:\n"
        "  openspec:\n"
        "    image: di-effect-agentic-openspec:local\n"
        "    build:\n"
        "      target: agentic-openspec\n",
        encoding="utf-8",
    )
    (tmp_path / "tools/agentic/README.md").write_text("OpenSpec\n", encoding="utf-8")
    env = tmp_path / ".config/env/tools/.env.tools.example"
    env.parent.mkdir(parents=True)
    env.write_text("DI_EFFECT_AGENTIC_OPENSPEC_VERSION=1.4.1\n", encoding="utf-8")
    for path in (
        "docs/operations/blueprint/bp-002-local-first-pluggable-architecture.md",
        "docs/operations/blueprint/bp-004-implementation-program-and-residue-erasure.md",
    ):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("current\n", encoding="utf-8")

    assert agentic_toolchain._collect_issues(tmp_path) == [
        ".config/env/tools/.env.tools.example must set "
        "DI_EFFECT_AGENTIC_OPENSPEC_VERSION=1.6.0"
    ]
```

- [ ] **Step 3: Run the new test and confirm current supply fails its intended contract**

Run:

```bash
cd /Users/yheng/projects/di-effect-task-openspec-1-6
pixi run pytest \
  tests/unit/di_effect_tooling/repo/runtime/checks/cli/test_agentic_toolchain.py -q
```

Expected: failure because both current supply files declare `1.4.1` and the checker has no exact-version contract.

- [ ] **Step 4: Add one exact-version constant and validate both supply surfaces**

In `agentic_toolchain.py`, add and use this contract:

```python
REQUIRED_OPENSPEC_VERSION = "1.6.0"
REQUIRED_DOCKERFILE_TOKENS = (
    "AS agentic-openspec",
    "@fission-ai/openspec",
    f"ARG OPENSPEC_VERSION={REQUIRED_OPENSPEC_VERSION}",
)
REQUIRED_ENV_VALUES = (
    f"DI_EFFECT_AGENTIC_OPENSPEC_VERSION={REQUIRED_OPENSPEC_VERSION}",
)
```

After reading the env text, append this exact issue when the value is absent:

```python
f"{TOOLS_ENV_EXAMPLE_REL} must set DI_EFFECT_AGENTIC_OPENSPEC_VERSION={REQUIRED_OPENSPEC_VERSION}"
```

Change the Docker `ARG`, the tracked environment value, and the README bullet to `1.6.0`.

- [ ] **Step 5: Run focused tests, the runtime checker, and OpenSpec validation**

Run:

```bash
cd /Users/yheng/projects/di-effect-task-openspec-1-6
pixi run pytest \
  tests/unit/di_effect_tooling/repo/runtime/checks/cli/test_agentic_toolchain.py \
  tests/unit/di_effect_tooling/repo/openspec_spec/cli/test_openspec_commands.py -q
pixi run di-effect repo check runtime agentic-toolchain
openspec validate --all --strict --json
```

Expected: the checker exits `0`, the unit tests pass, and strict OpenSpec validation reports zero failures.

- [ ] **Step 6: Commit only the di-effect task-worktree files**

Run:

```bash
cd /Users/yheng/projects/di-effect-task-openspec-1-6
git add tools/agentic/Dockerfile \
  .config/env/tools/.env.tools.example \
  tools/agentic/README.md \
  packages/di-effect-tooling/src/di_effect_tooling/repo/runtime/checks/cli/agentic_toolchain.py \
  tests/unit/di_effect_tooling/repo/runtime/checks/cli/test_agentic_toolchain.py
git diff --cached --check
git commit -m "build: pin agentic OpenSpec to 1.6.0"
```

Expected: the commit has no diff against the primary checkout's unrelated modified files.

## Task 5: Run cross-surface acceptance and preserve lane separation

**Files:**

- Verify only; do not create or edit historical evidence.

**Interfaces:**

- Consumes: Tasks 1-4 commits and regenerated host projections.

- Produces: fresh evidence that host and repository contract surfaces converge on OpenSpec `1.6.0`.

- [ ] **Step 1: Verify every current executable pin without scanning historical records**

Run:

```bash
rg -n '@fission-ai/openspec@1\.(4|5)\.0' \
  /Users/yheng/projects/ethos-worktrees/openspec-1-6-local-upgrade-20260711/packages \
  /Users/yheng/projects/ethos-worktrees/openspec-1-6-local-upgrade-20260711/tools \
  /Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6/pyproject.toml \
  /Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6/justfile \
  /Users/yheng/projects/di-effect-task-openspec-1-6/tools/agentic \
  /Users/yheng/projects/di-effect-task-openspec-1-6/.config/env/tools \
  /Users/yheng/projects/di-effect-task-openspec-1-6/packages/di-effect-tooling
```

Expected: exit `1` with no matches. Do not include `openspec/changes/archive/`, `docs/evidence/`, `evidence/`, or chronicles in this command.

- [ ] **Step 2: Re-run official validation in all three changed worktrees**

Run:

```bash
for root in \
  /Users/yheng/projects/ethos-worktrees/openspec-1-6-local-upgrade-20260711 \
  /Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6 \
  /Users/yheng/projects/di-effect-task-openspec-1-6; do
  (cd "$root" && openspec validate --all --strict --json)
done
```

Expected: three JSON summaries with zero failed items.

- [ ] **Step 3: Verify dual Codex command parity and generated skill provenance**

Run:

```bash
for home in \
  /Users/yheng/.codex \
  /Users/yheng/Library/Caches/JetBrains/PyCharm2026.1/aia/codex; do
  find "$home/prompts" -maxdepth 1 -type f -name 'opsx-*.md' -print | sort
done
rg -n 'generatedBy: "1.6.0"' \
  /Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6/.codex/skills \
  /Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6/.claude/skills
```

Expected: six command prompts per Codex home and six generated skill directories per tracked alphasim vendor projection.

- [ ] **Step 4: Inspect each worktree before lifecycle closeout**

Run:

```bash
git -C /Users/yheng/projects/ethos-worktrees/openspec-1-6-local-upgrade-20260711 status --short --branch
git -C /Users/yheng/projects/alphasim-dmgr-fix-b3-openspec-1-6 status --short --branch
git -C /Users/yheng/projects/di-effect-task-openspec-1-6 status --short --branch
```

Expected: only intended commits and no uncommitted mutations. Re-run each repository's native status/proof command before local lane closeout. Do not fast-forward an accepted root or publish a remote branch in this task.

## Plan Self-Review

### Spec coverage

- Exact `1.6.0` repository pinning: Tasks 2, 3, and 4.
- Core profile, `both` delivery, dual Codex prompts, and `/opsx:update`: Task 1 and Task 3.
- Official 1.6 archive/validation semantics: Tasks 2, 4, and 5 retain strict official validation and preserve non-zero failure propagation.
- Historical and foreign-worktree immutability: global constraints, Task 3 Step 1, Task 4 Step 1, and Task 5 Step 1.
- Local verification without lifecycle restart/publishing: Task 3 Step 4 and Task 5 Step 4.

### Placeholder scan

The plan contains no unresolved placeholder markers or deferred implementation labels. Each modification names a concrete source, test, literal, or command.

### Interface consistency

- The exact repository package literal is consistently `@fission-ai/openspec@1.6.0`.
- The di-effect environment name is consistently `DI_EFFECT_AGENTIC_OPENSPEC_VERSION`.
- The new OpenSpec workflow skill is consistently `openspec-update-change` and its Codex prompt is consistently `opsx-update.md`.
- Each repository is changed in its own Work Lane/worktree and verified before cross-surface checks.
