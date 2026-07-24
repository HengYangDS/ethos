## 1. Carrier And Lifecycle Admission

- [x] 1.1 Create proposal, design, Task list, contracts/quality deltas, material
  scope, active Claim, and dated Chronicle.
- [x] 1.2 Validate the Change strictly, validate ETHOS OpenSpec lifecycle and
  Claim health, bind the Claim to the owned Lane, and commit the bounded carrier.

## 2. Public Source And Bytes Boundaries

- [ ] 2.1 Write and observe RED for source-based ELOC and byte-based carrier and
  snapshot measurement APIs.
- [ ] 2.2 Implement delegation from existing file APIs and verify GREEN without
  private imports or duplicate parser logic.

## 3. Immutable Git Snapshot Adapter

- [ ] 3.1 Write and observe RED for commit/tree peeling, strict NUL `ls-tree`, one
  `cat-file --batch`, exact order/size/framing, and clean-HEAD worktree behavior.
- [ ] 3.2 Implement all-or-nothing snapshot and blob loads; reject symlink,
  gitlink, missing object, malformed/truncated/trailing data, dirty tracked or
  untracked worktree, and read failure.

## 4. Historical Replay And Shadow

- [ ] 4.1 Write and observe RED for the exact baseline identities, 933-file
  inventory digest, v1 `105342 -> 105060` replay, and the three category deltas.
- [ ] 4.2 Implement replay and selected C1 checkpoint observation without
  resolving or hiding its YAML adapter gap.
- [ ] 4.3 Write and observe RED for v1-authoritative shadow output and fail-closed
  disagreement classification, then implement minimal GREEN.

## 5. Tooling And Evidence

- [ ] 5.1 Write and observe RED for history configuration, CLI, shell wrapper,
  ignored artifact root, exit status, and `system/tools.toml` registration.
- [ ] 5.2 Implement GREEN, run focused and Task 2/3/C1 regressions, then run lint,
  types, config/schema/shell/module-layout/code-size/source-budget, lifecycle,
  Claims, and parity gates.
- [ ] 5.3 Refresh the Claim and Chronicle with reviewed replay/shadow digests,
  refresh generic parity, commit all tracked evidence, and run exact-HEAD default
  and full executed proof.

## Stop Boundary

Do not archive, land, close out accepted root, publish, push, modify foreign or
protected lanes, or retire this Lane as part of Task 4.
