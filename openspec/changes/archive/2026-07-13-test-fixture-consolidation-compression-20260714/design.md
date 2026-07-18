## Design

The three cases differ only by one finite state selector:

| Selector | Fixture state | Required gap |
| --- | --- | --- |
| `branch_missing` | no candidate branch | `candidate_branch_missing` |
| `worktree_missing` | candidate ref without linked checkout | `candidate_worktree_missing` |
| `worktree_dirty` | linked candidate checkout with residue | `candidate_worktree_dirty` |

One parametrized test owns the shared invocation and invariants. Case-local
setup remains in the test body because it is smaller and clearer than a new
helper abstraction. The change must be a source-budget net deletion. The
matrix remains bounded: adding a new unrelated admission dimension requires a
separate test or a new explicit matrix decision.

## Risks and rollback

A mistaken matrix can blur a state-specific assertion. Focused tests execute
all three generated cases. Revert this one test-file change if parity fails.
