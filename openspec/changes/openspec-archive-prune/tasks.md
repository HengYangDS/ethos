# Tasks

## 1. Prune the September archive

- [x] 1.1 Remove the 98 archive directories dated before 2026-10-01. Done when no tracked file
      outside the archive cites their paths, the 507 files are gone from the tree, and each stays
      readable at `v0.2.0-beta.9`. Evidence: 5f385190d removes the 98 directories, 507 files. Before
      it, `git grep` with the 98 directory names found no tracked file outside the archive that
      names them, and one citation inside the archived `one-proof-per-change` proposal, which
      history resolves; each of the 507 files was byte-identical at `v0.2.0-beta.9` and the lane
      head `0aa46818a`.

## 2. Acceptance

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
