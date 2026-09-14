## Context

The failed hosted closeout stack ends in source identity's `git read-tree` while
constructing display/bootstrap data. The same accepted source succeeds locally;
that does not erase the hosted failure. A current isolated profile of the exact
case takes 52.76 seconds, including 27 source compilations totaling 5.51 seconds
and 1,415 Git calls. Cumulative timings overlap and are not additive wall time.

A separate runtime fixture performs a real isolated `--version` smoke with a
ten-second timeout. Its import-time sample includes native Pydantic and YAML
loading. This batch must not silently remove that smoke or claim the two timeouts
have one fully proved cause.

## Decision

Keep source identity in its existing deep owner. Resolve HEAD once, read its
exact tree when no overlay is required, and otherwise retain the temporary-index
`read-tree`, `add -A`, `write-tree` semantics. Reobserve HEAD before returning.
Bound all Git steps by one 30-second source-observation deadline; carry native
argv, cwd, timeout and available output through the existing Git error type.
Public status and version output retain typed failures and derive a fresh status,
not a speculative reinstall. Normal source-index cleanup remains owned by the
operation's context manager.
This bounds observation, not arbitrary child processes, ref effects or crash GC.

Closeout helpers consume the existing narrow worktree-record and ref owners.
Rendering a command or bootstrap package must not trigger full runtime/Lease
admission. Each actual mutation still invokes fresh admission and exact CAS.
Reuse an explicitly supplied observation for one projection, not as authority.

## Alternatives

- Raising timeouts or parallelism leaves repeated work and uncertainty intact.
- Reusing the live index is not selected: a native probe showed copied
  assume-unchanged/skip-worktree flags can hide a changed file after read-tree.
- A cross-command source cache would need a complete freshness proof. HEAD or
  file-stat equality alone is not an acceptable substitute for current bytes.
- Replacing lifecycle fixtures with stubs could hide integration defects. Keep
  the existing end-to-end cases and isolate only the actual measured owner.

## Acceptance And Execution

1. Reproduce mixed HEAD coordinates, unbounded source observation and redundant
   closeout projection reads with distinguishing tests before implementation.
2. Repair the sole owners; test staged/unstaged, deletion, modes, untracked,
   ignored, worktree, failure and cleanup semantics against native Git.
3. Replay the exact historical cases with unchanged test timeouts and workers;
   compare equivalent profiles and report remaining costs and failures honestly.
4. Run affected native gates and package smoke, then exact proof, official
   archive, accepted closeout, installation, independent peers and lane retirement.

Existing per-file 500, independent 50,000 totals and combined 95-percent coverage
remain unchanged. No result cache, compatibility branch or duplicate parser is
added. Current full P0–P7 dependencies remain in the canonical terminal plan.
