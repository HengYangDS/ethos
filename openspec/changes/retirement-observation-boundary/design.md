# Design

## Context

Retirement of reviewed content deletes a lane's worktree only after the native
open-file observation finds no process holding its files; the requirement and
its scenarios are in the proposal and the spec delta. `lsof` runs as the
invoking user. On Linux it reads `/proc/<pid>/cwd`, `root` and `exe` and opens
`/proc/<pid>/fd`; for a process the user may not inspect, each read fails with
`Permission denied`, and those four records are all it prints for that process.
A process that turns non-dumpable or changes credentials after `lsof` opened its
descriptor directory leaves a denied descriptor record inside an otherwise
readable process. Darwin's `lsof` prints nothing for processes it may not
inspect.

## Goals / Non-Goals

**Goals:** make the observation boundary explicit and identical in meaning on
both platforms, keep every partial or unexplained failure fail-closed, and show
reviewers which processes the observation could not inspect.

**Non-Goals:** privileged observation, changing how hosted jobs run, or treating
an uninspectable process as proof that it holds nothing.

## Decisions

- **Uninspectable means every record is a denied `/proc` entry.** A process
  qualifies only when all its records are `cwd`, `rtd` or `txt` readlink
  denials or the `NOFD` opendir denial, each with exactly `Permission denied` in
  the C locale. Any readable record or other errno keeps it inside the
  observation and fails closed. The term is "uninspectable", not "foreign": a
  same-user non-dumpable agent or a setuid child matches too.
- **Partial denial is retried, not admitted.** A scan left incomplete by an
  unreadable record is taken again, at most three times within the observer's
  one 30-second timeout, so incomplete output still ends unknown in the same
  bound; malformed output is not retried. A persistent record still blocks.
- **Report, do not drop.** `lsof -F0pcuftDin` adds each process's command and
  user ID. The uninspectable list is `[]` when Linux observed none and `null` on
  Darwin, whose omission cannot be enumerated.
- **The removing admission is the reported one.** Every admission records its
  observation in the progress it produces; the terminal receipt and result carry
  the admission that ran immediately before the worktree was removed, including
  on `lane retire recover`.
- **The observer leaves the process adapter.** Open-file observation is its own
  semantic owner in `ethos.adapters.open_files`; process execution stays in
  `ethos.adapters.process`.

## Risks / Trade-offs

- A root, setuid or container process working in a lane is unseen on both
  platforms → The content review before disposal and the recheck after the
  observation remain the gates, and the report names every Linux process the
  observation could not inspect.
- A process that becomes uninspectable mid-scan can look partially readable and
  block → The bounded rescan observes it settled.
