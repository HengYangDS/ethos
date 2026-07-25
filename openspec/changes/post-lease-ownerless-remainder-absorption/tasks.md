## 1. Exact post-lease observation

- [x] 1.1 Re-observe all four branches, heads, registrations, merge bases,
  lease/Claim state, dirty state, and path occupancy.
- [x] 1.2 Bind exact status, cached patch, working patch, full-index patch, and
  untracked digests for the dirty compression lane.
- [x] 1.3 Reconstruct the exact dirty index and working state in isolation and
  prove all recorded digests match.

## 2. Semantic absorption

- [x] 2.1 Map every clean lane's durable intent to current accepted or
  valid-owner successor semantics and name rejected replay explicitly.
- [x] 2.2 Run focused and broader differential tests on the reconstructed dirty
  state and distinguish implementation findings from shared test-environment
  failures.
- [x] 2.3 Record the lane-specific `retire`, `retire`, `preserve-retire`, and
  `retire` dispositions in one digest-bound Chronicle and JSON record.
- [x] 2.4 Keep all valid-owner lanes observe-only.

## 3. Carrier lifecycle

- [x] 3.1 Pass strict OpenSpec lifecycle, Claim, docs, config, and focused
  governance checks.
- [x] 3.2 Refresh and commit generic parity evidence.
- [ ] 3.3 Execute exact-HEAD proof, complete only evidenced tasks, and officially
  archive this change.
- [ ] 3.4 Reprove the archive HEAD, refresh current base if necessary, land to
  candidate, and complete accepted-root closeout.

## Post-archive transition boundary

The following are later native effects, not unfinished tasks in this archived
Change: record and apply four separate decisions; verify three clean retirements
and one exact preservation package; create, prove, archive, land, and accept a
separate exact-manifest clear carrier; clear only that package; retire owned
carriers; and run final housekeeping. Remote publication and hosted observation
remain separate.
