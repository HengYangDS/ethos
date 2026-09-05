## Context

See `proposal.md`. The existing current-resolution report already retains the
official OpenSpec `status --json` and `validate --all --strict --json` results.
The validation command reports an invalid Change as one structured item whose
`issues[].path` values identify files relative either to the Change root or to
its `specs/` root. The existing validation-repair scope currently consumes only
the summarized canonical-spec gap and therefore cannot repair the selected
Change that produced the block.

## Goals / Non-Goals

**Goals:**

- Reuse the current official observations to derive exact active-Change repair
  paths.
- Keep one ephemeral validation-repair scope for canonical and active-Change
  validation failures.
- Preserve all surrounding mutation-admission checks and fail closed whenever
  an issue path is not uniquely attributable to one existing official regular
  file.

**Non-Goals:**

- Parse validator prose or infer a path from a requirement name.
- Authorize an absent destination, a Change directory, or every artifact in an
  invalid Change.
- Change Commitment compilation, OpenSpec schemas, Lease state, or persistence.
- Repair the downstream spec-free Commitment progress defect in this atom.

## Decisions

### Reuse the raw official command observations

The existing governance report remains the sole observation owner. The repair
scope reads its current selected Change, lifecycle artifact graph,
`commands.status.json`, and `commands.validate.json`; it does not add a new
report field or cache.

Alternative rejected: encode the issue path into a new required-gap string.
That would create another projection grammar and discard the already available
structured result.

### Resolve an issue path by unique intersection

For an invalid item whose type and id are exactly `change` and the selected
Change, each strict-blocking `ERROR` or `WARNING` issue path is normalized as a
repository-relative candidate under both the Change root and its `specs/`
root. Candidates are intersected with current official existing artifact
outputs plus the existing metadata file. Exactly one match becomes repairable;
zero or multiple matches grant no authority. `INFO` remains non-blocking and
never grants mutation authority.

Alternative rejected: prepend `specs/` unconditionally. OpenSpec also emits
Change-root-relative paths such as task files and `.openspec.yaml`; guessing a
single base would either miss valid repairs or authorize the wrong file.

### Preserve lexical artifact identity and require regular files

The existing official artifact projection retains the declared absolute path
as a lexical repository-relative path without resolving the final path. It
rejects relative, outside-root, and traversing declarations. The repair owner
then uses `lstat` to require that exact path to be a regular file, so a symlink
cannot replace an official artifact or make its target appear official.

Alternative rejected: resolve the declared artifact before relativizing it.
Path resolution follows symlinks and can transfer official identity from the
declared artifact to an unrelated target.

### Replace the narrow owner rather than add a parallel one

The canonical-only repair helper becomes the general official validation repair
owner. Canonical-spec behavior and tests remain, active-Change behavior is
added, and the old symbol exits rather than surviving as a facade.

Alternative rejected: add a second active-Change repair resolver. Two owners
would compete over the same prewrite decision and repeat the authority split
this convergence is removing.

### Keep repair authority ephemeral and postcondition-bound

Every prewrite re-runs official observation. The reported continuation remains
strict OpenSpec validation; once validation passes, no matching issue remains
and ordinary Commitment attribution resumes.

Alternative rejected: mint a repair receipt or durable exception. It would
turn one current fact into reusable permission.

## Risks / Trade-offs

- **OpenSpec emits a non-file field path such as `file` or
  `requirements[0]`** → no official output matches, so prewrite remains
  blocked rather than guessing.
- **A path can resolve under both official bases** → ambiguity yields no
  repair authority.
- **An official output or metadata path is a symlink** → the exact path is not
  a regular file and receives no repair authority.
- **The artifact graph or issue changes between observations** → normal
  prewrite and hook re-observation invalidates the stale decision.

## Migration Plan

Add focused failing resolution tests, replace the existing repair owner, run
the focused admission and OpenSpec lifecycle tests, then use the resulting
runtime to repair and resume the blocked spec-free Change. No stored state or
adopter migration is required.
