# Local CI Git Bundle Locale Robustness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox syntax for tracking.

**Goal:** Keep complete-history bundle verification deterministic across host
message locales without changing product behavior.

**Architecture:** Localize the determinism boundary to the single external Git
assertion. The test copies the process environment, overrides `LC_ALL` and
`LANG` with `C`, invokes Git directly, and retains the semantic output check.

**Tech Stack:** Python 3.12+, pytest, Git, ETHOS owner scripts.

## Global Constraints

- Product code and shared Git helpers remain unchanged.
- Remote publication remains deferred.
- All tracked writes occur in the owned Work Lane.

---

### Task 1: Deterministic Bundle Verification

**Files:**

- Modify: `tests/unit/cli/lane/test_cross_host_handoff.py`

**Interfaces:**

- Consumes: the bundle produced by `_export`.
- Produces: a C-locale `git bundle verify` observation for the existing
  complete-history assertion.

- [x] **Step 1: Confirm RED**

Run the existing focused test with `LC_ALL=zh_CN.UTF-8` and confirm it fails
because the output is localized rather than because the bundle is invalid.

- [x] **Step 2: Add the minimal locale boundary**

Add `import os`, then replace the helper assertion with:

```python
verification = subprocess.run(
    ["git", "bundle", "verify", (package_dir / "repository.bundle").as_posix()],
    cwd=worktree,
    check=True,
    capture_output=True,
    text=True,
    env={**os.environ, "LANG": "C", "LC_ALL": "C"},
)
assert "complete history" in verification.stdout
```

- [x] **Step 3: Verify GREEN**

Run the focused test under the workstation locale and expect one passing test.

- [ ] **Step 4: Run governed closeout gates**

Run Python lint, full local CI fallback, parity refresh, strict OpenSpec,
HEAD-bound proof, archive, candidate land, accepted-root closeout, and owned
lane retirement.
