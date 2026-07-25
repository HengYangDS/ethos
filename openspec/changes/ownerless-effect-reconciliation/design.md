## Context

The accepted absorption carrier selected direct `retire` for three clean
ownerless lanes and `preserve-retire` for one dirty lane. The dirty effect
completed with an exact verified package. Each clean effect reached WCP and was
rejected before mutation because the source is diverged rather than an accepted
ancestor. Branches, worktrees, and refs therefore remain unchanged.

## Decisions

### 1. Preserve the WCP fail-closed boundary

The reconciliation does not reinterpret semantic absorption as Git ancestry.
It does not alter WCP, manufacture an ancestor relation, or use raw worktree/ref
deletion. The three direct-retire decisions remain truthful no-effect records.

### 2. Use transient preservation as an effect bridge

A new accepted decision may select `preserve-retire` for each exact clean lane.
This is not blanket preservation and does not reverse the semantic judgment.
The bundle exists only to make removal recoverable under the currently supported
native effect path. Because the lanes are clean, staged and working patches must
remain empty.

### 3. Reuse one staged carrier

Stage 1 records the WCP boundary, authorizes the three exact bridge effects, and
binds the already-known dirty manifest clear. After Stage 1 is proved, landed,
and accepted, native effects run outside tracked source. The same Work Lane then
records the resulting exact decision IDs and manifest SHA-256 values, completes
its active tasks, archives, re-proves, lands, and accepted-closes Stage 2.

### 4. Clear only exact accepted manifests

`lane_resolution/clear-preservation` is allowed only for a decision ID and
manifest SHA-256 recorded by accepted Chronicle bytes. A mismatch, missing
receipt, duplicate package, renewed owner, changed ref, changed path occupancy,
or package-integrity gap blocks the transition. Successful clear removes only
the retained package and keeps its immutable decision, completion receipt, and
clear receipt.

## Risk Controls

- no force flags and no raw branch/worktree deletion;
- exact branch, head, decision, observation, and manifest bindings;
- no valid-owner lane mutation or authority transfer;
- one package clear per command with dry-run before apply;
- clean bridge packages are temporary and must not be described as product
  truth;
- GitLab remains unreachable off intranet and outside local closeout.
