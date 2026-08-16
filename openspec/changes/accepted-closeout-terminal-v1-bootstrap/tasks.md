# Tasks

- [x] **1. Reproduce the fail-late closeout.** Verify dry-run passes while apply
  rejects the terminal-v1 accepted HEAD.
- [x] **2. Carry exact prestate coordinates.** Reuse existing bootstrap admission
  without adding another authority or compatibility path.
- [x] **3. Prove focused behavior.** Cover exact prestate and retain existing
  closeout, landing, and failure-matrix behavior.
- [x] **4. Complete lifecycle evidence.** Commit, execute exact-HEAD proof,
  archive, land, close out, retire, and verify the package-only runtime.

| Outcome | Task | Evidence |
| --- | ---: | --- |
| `command-plane:Accepted closeout preserves exact bootstrap identity` | 1 | `receipt:accepted-closeout-rejection` |
| `adapters:Terminal-v1 prestate remains fail-closed` | 2 | `tests:accepted-bootstrap-prestate` |
| `quality:Focused closeout behavior remains green` | 3 | `tests:accepted-closeout-focused` |
| `lifecycle:Forward fix reaches accepted package-only runtime` | 4 | `proof:exact-head` |
