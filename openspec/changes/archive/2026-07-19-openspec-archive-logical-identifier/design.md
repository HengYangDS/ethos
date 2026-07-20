## Context

The official OpenSpec active list returns logical Change IDs, while archived
directories use `YYYY-MM-DD-<logical-id>`. ETHOS currently passes a requested
`--change` directly to the official active-status command, so an archive
directory name receives a late generic failure instead of a clear category
error. Historical carriers are immutable evidence and must not be renamed to
adapt a reader.

## Goals / Non-Goals

**Goals:**

- Separate active Change selection from archive lookup.
- Resolve a logical archive ID only when exactly one dated archive suffix
  matches it.
- Return stable, machine-readable failure gaps for malformed, missing, and
  ambiguous archive queries.

**Non-Goals:**

- Reconstructing or promoting an archived Change into the active lifecycle.
- Creating a vendor-specific task or worktree registry.
- Changing official OpenSpec archive naming.

## Decisions

1. **Keep archive resolution in a pure ETHOS reader.** It scans only
   `openspec/changes/archive` and returns a relative carrier path; it does not
   invoke archive mutation or alter historical files.
2. **Use `--archive-id` as a distinct selector.** It accepts the logical
   suffix, while `--change` remains an active Change selector. Supplying both
   fails closed.
3. **Reject archive-directory syntax before active status.** The reader reports
   a precise gap rather than forwarding a dated directory name to the active
   official CLI.

## Risks / Trade-offs

- [Two archives share a logical suffix] → report ambiguity rather than selecting
  by date.
- [A caller keeps passing a dated directory name] → return a corrective gap
  that names the distinct archive selector.
- [Historical carrier is malformed] → query identity remains read-only; archive
  closeout validation continues to assess historical completeness separately.
