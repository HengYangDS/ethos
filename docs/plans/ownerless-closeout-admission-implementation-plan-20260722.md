---
subject: ethos:ownerless-closeout-admission-implementation-plan-20260722
role: plan
state: active
relations:
  implements: ownerless-closeout-admission-design-20260722
---

# Ownerless Closeout Admission Implementation Plan

Status: approved implementation plan; no implementation task has started.

Purpose: convert the approved ownerless closeout design into a tested, fail-closed cross-component delivery sequence.

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permit only a clean, semantically absorbed, ownerless linked Work Lane to retire through an accepted decision and a fresh fail-closed closeout check, while making new ETHOS lanes conform to the repository-family branch/path grammar.

**Architecture:** ETHOS keeps semantic authority: it writes and re-observes an exact resolution decision. Immediately before the destructive native effect, an adapter invokes repository-family admission in a new ownerless-decision mode. The workstation validator verifies its own Git/worktree facts plus the decision bindings; ETHOS then performs its existing no-force removal/ref-CAS and writes the completion receipt only after postconditions pass.

**Tech Stack:** Python 3.14, pytest, ETHOS CLI/adapters, Git worktree porcelain, workstation repository-family Python CLI, zsh artifact deployment checks.

## Global Constraints

- Never synthesize or replace an historical owner; record an executor only.
- The ownerless path accepts only `clean + linked + missing lease + missing claim + accepted ancestor + exact decision`.
- Dirty, diverged, valid-owner, claim-bound, stale-head, Chronicle-drift, malformed-layout, and receipt-mismatch states fail closed.
- The retirement effect remains `no-force`; raw Git worktree/ref deletion remains forbidden.
- New lanes use `work/YYYYMMDD-task-slug` and `repo-worktrees/YYYYMMDD-task-slug`.
- Legacy lanes are migration-required; this change does not rename or remove them.
- Workstation deployment is source-built and verified; do not hand-edit an installed artifact.

---

## File Map

- Modify: `packages/ethos/src/ethos/adapters/mutation/lanes.py` — create canonical date-bound branch/path pairs.
- Modify: `packages/ethos/src/ethos/adapters/mutation/lane_lifecycle/core.py` — centralize lane identity parsing and canonical sibling path derivation.
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/lane.py` — invoke the ownerless closeout preflight before `retire_lane`.
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/_effects.py` — carry the validated preflight result into the exact no-force native effect and receipt.
- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/repo_family.py` — bounded subprocess adapter for the workstation closeout check; it parses only JSON and maps failures to stable gaps.
- Modify: `tests/unit/lanes/test_lanes_lifecycle.py` — date-bound start and legacy-name rejection coverage.
- Modify: `tests/unit/lanes/retirement/test_unbound_and_helpers.py` — clean ownerless preflight and refusal matrix.
- Create: `tests/unit/lanes/retirement/test_ownerless_closeout_admission.py` — adapter contract and effect-order tests.
- Modify: `docs/reference/command-plane.md` — document ownerless decision admission and executor boundary.
- Modify: the tracked source that deploys `~/.config/workstation/repo_family_governance.py` — add ownerless-decision closeout validation, CLI flags, and its source tests; rebuild the workstation artifact through its existing build script.

## Task 1: Establish canonical lane identity at creation time

**Files:**
- Modify: `packages/ethos/src/ethos/adapters/mutation/lane_lifecycle/core.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/lanes.py`
- Modify: `tests/unit/lanes/test_lanes_lifecycle.py`

**Interfaces:**
- Produces `canonical_lane_identity(name: str, *, observed_at: datetime) -> tuple[str, str]` returning `(lane_id, branch)`.
- Produces `canonical_lane_path(repo: Path, lane_id: str) -> Path` returning the governed sibling worktree path.
- `start_work_lane` uses these functions and refuses an explicit path that does not equal the canonical path.

- [ ] **Step 1: Write failing tests for canonical branch/path generation**

```python
def test_start_work_lane_uses_date_bound_family_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(lanes, "utc_now", lambda: datetime(2026, 7, 22, tzinfo=UTC))
    report = lanes.start_work_lane(
        root=repo,
        name="ownerless closeout admission",
        holder_ref=HOLDER,
        apply=False,
    )
    assert report["branch"] == "work/20260722-ownerless-closeout-admission"
    assert report["path"] == str(tmp_path / "repo-worktrees" / "20260722-ownerless-closeout-admission")
```

- [ ] **Step 2: Run the focused test and verify the old implementation fails**

Run: `uv run --all-packages --group dev pytest -q tests/unit/lanes/test_lanes_lifecycle.py::test_start_work_lane_uses_date_bound_family_identity --no-cov`

Expected: failure because the current branch is `work/ownerless-closeout-admission` and the default path is not under the sibling `repo-worktrees` root.

- [ ] **Step 3: Implement the smallest identity helpers and wire them into `start_work_lane`**

```python
def canonical_lane_identity(name: str, *, observed_at: datetime) -> tuple[str, str]:
    lane_id = f"{observed_at.astimezone(UTC):%Y%m%d}-{slug(name)}"
    return lane_id, f"work/{lane_id}"


def canonical_lane_path(repo: Path, lane_id: str) -> Path:
    return repo.parent / f"{repo.name}-worktrees" / lane_id
```

Reject an explicit `path` whose resolved value differs from `canonical_lane_path`; return `lane_start_path_not_canonical` without creating a branch or lease.

- [ ] **Step 4: Run lane-start lifecycle coverage**

Run: `uv run --all-packages --group dev pytest -q tests/unit/lanes/test_lanes_lifecycle.py -k 'start_work_lane' --no-cov`

Expected: PASS, including existing candidate-cleanliness and lease tests.

- [ ] **Step 5: Commit the self-contained ETHOS lane-identity change**

```bash
git add packages/ethos/src/ethos/adapters/mutation/lane_lifecycle/core.py \
  packages/ethos/src/ethos/adapters/mutation/lanes.py \
  tests/unit/lanes/test_lanes_lifecycle.py
git commit -m "fix(lanes): create canonical date-bound work lanes"
```

## Task 2: Add a repository-family ownerless-decision preflight

**Files:**
- Modify: the tracked source that deploys `~/.config/workstation/repo_family_governance.py`
- Modify: its colocated source tests and artifact build verification

**Interfaces:**
- Add CLI flags `--ownerless-decision <absolute-json-path>` and `--executor-ref <holder-ref>` to `worktree-closeout-check`.
- Preserve `--owner-task` for the existing owner-bound route; exactly one route is required.
- Return `action="worktree_closeout_check"` plus `admission_mode="ownerless_decision"` on success.

- [ ] **Step 1: Write failing validator tests**

```python
def test_ownerless_decision_closeout_accepts_clean_accepted_ancestor(tmp_path):
    decision = decision_fixture(branch="work/20260722-clean", head=HEAD, clean=True)
    report = worktree_closeout_check(
        repo=repo, branch="work/20260722-clean", path=lane_path,
        ownerless_decision=decision, executor_ref="agent:codex:thread:executor",
    )
    assert report["ok"] is True
    assert report["admission_mode"] == "ownerless_decision"
```

Add parameterized refusal cases for active lease, claim, dirty state, non-ancestor head, stale decision head, Chronicle digest drift, wrong lane path, malformed decision JSON, and a supplied owner task.

- [ ] **Step 2: Run the validator tests and verify ownerless admission is absent**

Run the repository-family source test command from its authoritative checkout.

Expected: failure because `worktree_closeout_check` currently requires `owner_task == lane_id` unconditionally.

- [ ] **Step 3: Implement the mutually exclusive admission routes**

```python
if ownerless_decision is not None:
    _validate_executor(executor_ref)
    _validate_ownerless_decision(
        decision=load_json_no_symlink(ownerless_decision),
        branch=branch, head=head, path=candidate, base=base,
    )
    admission_mode = "ownerless_decision"
else:
    _validate_owner_task(owner_task, lane_id)
    admission_mode = "owner_bound"
```

The ownerless validator must verify: decision disposition is `retire`; decision observation names the exact branch/head/path; decision Chronicle is inside accepted `evidence/chronicle`; the Chronicle digest matches; the registered worktree is clean; no active lease or claim exists; and the head is an ancestor of the selected accepted base.

- [ ] **Step 4: Run validator and artifact-build verification**

Run the authoritative repository-family test suite, then its build-artifact test. Install only through that project’s established source-build/deployment command; re-run `workstation repo-family worktree-closeout-check --help` to verify both flags are visible.

Expected: PASS; existing owner-bound tests still pass unchanged.

- [ ] **Step 5: Commit and deploy the workstation component separately**

Commit only the authoritative workstation-control-plane source, tests, and artifact metadata. Verify the deployed command hash/version against the built artifact before using it from ETHOS.

## Task 3: Integrate preflight into ETHOS resolution before the destructive effect

**Files:**
- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/repo_family.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/lane.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/_effects.py`
- Create: `tests/unit/lanes/retirement/test_ownerless_closeout_admission.py`

**Interfaces:**
- `ownerless_closeout_preflight(*, root: Path, decision_path: Path, observation: LaneObservation, executor_ref: str) -> dict[str, object]`
- The adapter runs only `workstation repo-family worktree-closeout-check`, requires JSON, and never executes removal.
- `prepare_resolution_effect` accepts a successful preflight binding and refuses a `retire` effect without it.

- [ ] **Step 1: Write a failing effect-order test**

```python
def test_retire_runs_ownerless_preflight_before_worktree_removal(monkeypatch, decision, observation):
    calls = []
    monkeypatch.setattr(resolution, "ownerless_closeout_preflight", lambda **_: calls.append("preflight") or {"ok": True})
    monkeypatch.setattr(resolution, "retire_lane", lambda **_: calls.append("retire"))
    resolution.apply_lane_resolution(..., apply=True, confirm_irreversible=True)
    assert calls == ["preflight", "retire"]
```

Add tests that a non-JSON response, nonzero command, stale observation, or `ok=false` preflight yields a stable required gap and leaves the worktree/ref untouched.

- [ ] **Step 2: Run the focused test and verify the current code retires without preflight**

Run: `uv run --all-packages --group dev pytest -q tests/unit/lanes/retirement/test_ownerless_closeout_admission.py --no-cov`

Expected: failure because `apply_lane_resolution` currently calls `retire_lane` directly.

- [ ] **Step 3: Implement the subprocess adapter and pre-effect guard**

```python
report = ownerless_closeout_preflight(
    root=root,
    decision_path=decision_path,
    observation=observation,
    executor_ref=os.environ.get("ETHOS_ACTOR", "").strip(),
)
if not report.get("ok"):
    return stop(str(report["required_gaps"][0]))
retire_lane(root=root, observation=observation)
```

Pass the exact decision path, branch, head, path, accepted base, and executor to the command. Do not accept a result missing `admission_mode == "ownerless_decision"`.

- [ ] **Step 4: Run retirement regression suites**

Run:

```bash
uv run --all-packages --group dev pytest -q --no-cov \
  tests/unit/lanes/retirement/test_ownerless_closeout_admission.py \
  tests/unit/lanes/retirement/test_unbound_and_helpers.py \
  tests/unit/lanes/test_lanes_lifecycle.py
```

Expected: PASS; valid-owner and dirty paths remain blocked.

- [ ] **Step 5: Commit the ETHOS integration**

```bash
git add packages/ethos/src/ethos/adapters/mutation/resolution \
  tests/unit/lanes/retirement/test_ownerless_closeout_admission.py \
  tests/unit/lanes/retirement/test_unbound_and_helpers.py
git commit -m "feat(lanes): admit ownerless retire through accepted decision"
```

## Task 4: Document and prove the integrated contract

**Files:**
- Modify: `docs/reference/command-plane.md`
- Modify: `docs/plans/ownerless-closeout-admission-design-20260722.md` only if the implementation changes an approved interface
- Modify: targeted CLI contract tests when the command output changes

**Interfaces:**
- Documentation names the ownerless decision route as pre-effect, target-specific, executor-recording, and fail-closed.
- CLI output names `ownerless_decision` without exposing it as a generic takeover authority.

- [ ] **Step 1: Write failing documentation/CLI contract assertions**

```python
def test_ownerless_preflight_output_is_not_generic_takeover():
    payload = invoke_ownerless_preflight(...)
    assert payload["admission_mode"] == "ownerless_decision"
    assert "takeover" not in json.dumps(payload).lower()
```

- [ ] **Step 2: Run the focused contract tests**

Run the exact ETHOS CLI contract test selected by the changed command surface and the docs registry gate.

Expected: PASS after the new wording and output are present.

- [ ] **Step 3: Update command-plane documentation**

Document all required flags, exact preconditions, refusal cases, the no-force effect, and the distinction between ownerless executor and valid owner. Add no generic cleanup command.

- [ ] **Step 4: Execute the full ETHOS proof on a stable head**

```bash
ETHOS_ACTOR='<current-holder-ref>' \
  tools/ci/scripts/run-ethos-lane.sh prove --execute --expect-head "$(git rev-parse HEAD)" --json
```

Expected: all required gates pass and proof evidence is bound to the current lane head.

- [ ] **Step 5: Commit documentation and proof-facing contract updates**

```bash
git add docs/reference/command-plane.md tests/unit/cli
git commit -m "docs(lanes): define ownerless closeout admission"
```

## Task 5: Controlled rollout against one clean ownerless target

**Files:**
- Create: one immutable record below the governed `ethos-records/evidence/<UTC>-ownerless-closeout-pilot/` root, admitted with `record-admit`

**Interfaces:**
- Select exactly one current clean ownerless accepted ancestor with a canonical branch/path pair.
- The record includes `README.md`, `closeout.json`, `MANIFEST.json`, and `SHA256SUMS` and is verified before index update.

- [ ] **Step 1: Re-observe all target facts without mutation**

Run `ethos lane status --json`, `git worktree list --porcelain`, the selected target’s porcelain status, current branch/head relation, active lease/claim lookup, and ownerless decision dry-run.

Expected: selected target remains clean, linked, missing lease/claim, canonical, and an accepted ancestor.

- [ ] **Step 2: Run the ownerless closeout preflight dry-run**

Run `workstation repo-family worktree-closeout-check` with the exact ownerless decision and executor flags.

Expected: `ok=true`, `admission_mode=ownerless_decision`, exact branch/head/path bindings, and no active path users.

- [ ] **Step 3: Apply native resolution once**

Run `ethos lane resolution apply --decision-path <exact-path> --confirm-irreversible --apply --json`.

Expected: no-force worktree removal, head-bound ref deletion, and a new native receipt after verified postconditions.

- [ ] **Step 4: Re-observe and seal a recovery/evidence record**

Verify the target ref and worktree absence, decision/receipt bindings, accepted HEAD, and record manifest hashes. Do not modify previously verified records.

- [ ] **Step 5: Land/close out only the implementation lane through normal lifecycle**

Run `status -> plan -> prove --execute -> land -> accepted closeout`; retire the implementation lane only if its own branch/path conforms to the corrected grammar and its closeout check passes.

## Plan Self-Review

- Spec coverage: Tasks 1–3 implement canonical creation and pre-effect ownerless admission; Task 4 supplies command/documentation evidence; Task 5 validates the route against one real clean lane without broad cleanup.
- Boundary coverage: every prohibited state has a direct refusal test in Tasks 2–3.
- Placeholder scan: no deferred or unspecified implementation steps remain; the workstation component is deliberately named as its tracked source because the deployed configuration file is not authoritative source.
- Type consistency: the decision is the pre-effect input throughout; the receipt is only a post-effect artifact.

## See Also

See also: [Ownerless Closeout Admission Design](ownerless-closeout-admission-design-20260722.md) and [Ownerless First-Batch Retirement](ownerless-first-batch-retirement-20260722.md).
