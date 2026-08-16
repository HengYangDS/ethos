# Tasks

- [x] **1. Reproduce the fail-late closeout.** Verify dry-run passes while apply
  rejects the terminal-v1 accepted HEAD.
- [x] **2. Carry exact prestate coordinates.** Reuse existing bootstrap admission
  without adding another authority or compatibility path.
- [x] **3. Prove focused behavior.** Cover exact prestate and retain existing
  closeout, landing, and failure-matrix behavior.

After Task 3 completes, close this Change only through the existing governed
lifecycle: execute exact-HEAD full proof; archive that proven HEAD; execute
full proof on the resulting archive HEAD; land and close out that proven
archive HEAD; retire the lane; then perform an accepted package-only readback.
These are post-task effects evidenced by their exact receipts and Attestations,
not OpenSpec tasks that may be checked before those effects occur.

| Outcome | Task | Evidence |
| --- | ---: | --- |
| `command-plane:Accepted closeout preserves exact bootstrap identity` | 1 | `receipt:accepted-closeout-rejection` |
| `adapters:Terminal-v1 prestate remains fail-closed` | 2 | `tests:accepted-bootstrap-prestate` |
| `quality:Focused closeout behavior remains green` | 3 | `tests:accepted-closeout-focused` |
