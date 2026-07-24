## Context

Task 2 defined immutable carrier and metric identities. Task 3 and accepted C1
made native measurement deterministic and resource-fail-closed. Task 4 must now
observe historical Git trees without materializing them and compare v1 authority
with an inactive v2 observer.

The declared v1 baseline came from provenance beginning `540e06d5`; that
provenance is not the replay treeish. The replay subject is exact commit
`2dab77f169eceb2d45f917358c2a7487e7ac8db6`, whose tree is
`075da5ad45be962e9f5e775b3f050cab4023ea0d`. Observer taxonomy is an independent
coordinate. Historical observer profile `v1-continuation-20260719` binds commit
`604934c7afe244caf5b671423f108823a7753a98`, taxonomy blob
`51a3931b43aa9030e166309289d6d85a80831526`, and content SHA-256
`b5dfc532586b0e1f3c3f614ce34e70cd9e817b84adfeabfbda266adf19d07a3d`.
Live profile `v1-live-at-task4-start` binds commit
`fe94c0268d060742e808770d4d65d554709af0dd`, taxonomy blob
`280f4ff640b0d6088c6fc819bebca2c6a7de5fea`, and content SHA-256
`3180f9739fc254c29fa6ca6924818a2c3eb5d1ccedd0fe1916e88a05e1b41983`.
The second selected checkpoint is accepted C1 commit
`3468ce78e2b636b9c0516904aa73cde2eb30fa62`; its known YAML adapter gap remains
blocked.

## Decisions

1. **Git objects are the immutable source.** `tree_snapshot(root, treeish)`
   resolves one full commit and tree identity and reads only Git object data.
   It never checks out, resets, switches, stashes, or creates a worktree.
   `worktree_snapshot(root)` is only a clean-HEAD convenience and rejects any
   tracked or untracked dirt before delegating to immutable HEAD objects.

2. **Identity is established before content.** The adapter first peels the
   treeish and parses strict NUL-framed recursive `git ls-tree` records. Each
   record must have canonical mode/type/OID/path framing, repository-relative
   normalized paths, unique ascending order, and an admitted regular-file mode.
   Symlinks, gitlinks, malformed records, missing objects, duplicates, invalid
   order, and command failure reject the complete load.

3. **One batch owns selected blob reads.** Selected blob OIDs are sent once, in
   inventory order, to one `git cat-file --batch` process. Every response header,
   OID, type, declared size, payload length, separator, response order, EOF, and
   trailing byte is verified. A missing/truncated/misordered/extra response or
   any read failure returns no partial observation.

4. **Public byte/source APIs own semantics.** The kernel exposes
   `effective_code_lines_for_source(source: str) -> int`. Repository measurement
   exposes `measure_carrier_bytes(...)` and `measure_snapshot_bytes(...)`.
   Existing path-based APIs read once and delegate. Immutable replay never
   imports private content functions and never copies parser logic.

5. **The historical v1 declaration and observer profiles are immutable.**
   Profile `v1-continuation-20260719` reports declared `105342`, replayed
   `105060`, and drift `-282`. The only category differences are JavaScript
   `+1`, YAML `-282`, and diagram `-1`; Jinja remains `671`. Its governed
   inventory has 933 files and digest
   `f8e85ace7648b60592fbe6e678f78169afa98c6289b0e8bb7d7fbc3961fa1c8d`.
   Live profile `v1-live-at-task4-start` intentionally reflects the later Jinja
   taxonomy removal: 888 files, digest
   `d48fca7255274216d029c600b98972f00bd367b91979441b4d6512a857fb7a5c`,
   global `104389`, and no Jinja coordinate. That taxonomy-profile drift is a
   separate unresolved disagreement; it neither rewrites nor replaces the
   reviewed historical correction.

6. **Shadow is observation, never authority.** Existing v1 top-level `ok`,
   `state`, and `required_gaps` remain authoritative. `v2_shadow.mode` is
   `v1_authoritative_v2_shadow`, `authoritative` is `v1`, and the observer binds
   its identity/digests, subject commit/tree/snapshot digest, v1 declaration and
   replay, v2 coordinates/digests/provider coverage or null, disagreements,
   required gaps, and comparison state. Missing v2 observation or any unresolved
   mismatch is `blocked`, `unresolved`, or `reviewed_observation`; it is never
   `clean` or `enforced`.

7. **History is declarative and artifacts are separated.**
   `.config/checks/source-budget/history.toml` declares exact checkpoints. The
   repository-owned CLI and shell wrapper write raw JSON only beneath ignored
   `build/evidence/quality/source-budget-v2/replay/`. Tracked Claim/Chronicle
   files record reviewed summaries and digests, not raw per-file observations.

## Failure Semantics

Every adapter or measurement failure is fail closed and redacted. A failed
snapshot exposes stable gaps and no entries/blob payloads/measurements/snapshot
digest. Replay default exit status is non-zero only for invalid configuration, failed
load/measurement, unexpected declared identity/count/digest, or a comparison
state outside the history entry's configured expected states. Expected
`reviewed_observation`, `unresolved`, and `blocked` results are valid transport
observations and do not fail the default command. An explicit `--require-clean`
mode returns non-zero unless every selected entry is `reviewed_observation` with
no required gaps. Ordinary `source_budget_report` never executes historical or
C1 replay; it only reduces a supplied observation or reports nested observation
absence while preserving top-level v1 authority.

## Rollback

Remove the replay/shadow adapter, CLI, wrapper, history config, tool declaration,
and Task 4 report extension together. Keep v1 unchanged and authoritative. Raw
ignored observations may be discarded without altering repository truth.

## Acceptance

- The baseline and C1 checkpoints bind their exact commit/tree identities.
- Strict Git framing and batch-protocol adversarial cases fail closed without a
  checkout, worktree, or partial observation.
- Exact historical-profile baseline replay yields 933 files, the required
  inventory digest, total `105060`, drift `-282`, and only the three declared
  category deltas; the live profile separately yields 888 files, its exact
  digest, `104389`, and an unresolved absent-Jinja disagreement.
- Shadow output preserves v1 authority and never classifies unresolved
  disagreement as clean.
- Focused and broader quality, lifecycle, Claim, parity, and exact-HEAD proof
  gates pass before reporting completion.
