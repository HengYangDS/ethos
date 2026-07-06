# Design

The transition's success state must be judged by repository truth, not only by a
subprocess return code. After accepted-ref CAS and worktree sync, ETHOS checks the
accepted checkout's porcelain status. Only an empty status may produce
`accepted_validated`.

The same principle applies to OpenSpec carriers. Audit and CLI aggregation already
surface active or completed-unarchived OpenSpec changes, but transition admission
must fail closed even when callers invoke the mutation adapter directly. The land
and closeout admission path now treats completed Work Lane carriers and any active
candidate or accepted-root carriers as blockers.

This adds no new command, store, or ontology. It moves an existing small signal
from a reader/audit surface into the existing transition precondition, preserving
OpenSpec as carrier rather than truth center.
