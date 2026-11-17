# Proposal

## Why

The entry of 0.2.0-beta.11 lists under Fixed that `ethos lane format` and the source-format,
Markdown, prose, link and configuration gates leave alone a path that Git attributes mark
`linguist-vendored` or `linguist-generated`. That fix asks Git for each path's attributes, and
Git also answers from sources that no commit carries: the `info/attributes` file of the Git
directory and a file that `core.attributesFile` names. A proof binds neither. A third source has
the same effect: a `.gitattributes` file of the worktree that the Git directory's exclude file
hides, which Git's status does not name and the proof's source binding does not see.

Measured on 2026-11-17 with each commit's own product code, on a committed document with two
misspellings: at 0.2.0-beta.10 the prose gate blocks as committed, blocks with one line in
`info/attributes` that marks the document generated, and blocks with the line removed. At the
release head it blocks, passes and blocks, and the proof's source binding holds each time. So a
local proof at the release head can pass on a file that it did not read. The defect came with
this release, by its own fix. The release lead measured the hidden worktree file the same way on
2026-11-18: 0.2.0-beta.10 blocks in all three states, and the release head passes in the second.

The owner decided on 2026-11-17 that the repair enters 0.2.0-beta.11, so the release head moves
once more before the tag.

## What Changes

- The authored selection reads its marks from the `.gitattributes` files that Git tracks or
  would add, and from no other source. A mark from the Git directory, from a configured
  attributes file or from a worktree file that an exclude rule hides no longer takes a path out
  of the format command or of a gate.
- The format gate's text validity check skips a path that Git's own reading marks, as it did in
  0.2.0-beta.10, so that no tree that passed the predecessor meets a new refusal.
- The accepted requirement on received paths names the files that count.

Out of scope: the readers that already followed Git's reading in 0.2.0-beta.10, which are path
admission, the staged size and text checks, and the paradigm report and its repair. Their use of
local state is a design question of 0.3.0, the subject of the draft `local-git-state-binding`. No
result names a local mark: reporting local Git state is not part of this Change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: the requirement "Received paths are not authored inputs" names the
  attribute source that counts and gains one scenario for a local line.

## Impact

`src/ethos/adapters/repo/git_attributes.py` gains the selection's reader, and
`src/ethos/adapters/gates/native/inputs.py` uses it. The owner of the source binding,
`src/ethos/adapters/repo/worktree_postimage.py`, gains one parameter. Each authored selection
makes one temporary directory and starts several more Git processes: about 0.2 seconds on this
repository's 1,606 Markdown paths, where Git's own reading takes about 0.01. Patterns match by
exact case.
The entry of 0.2.0-beta.11 amends its Fixed item. The release head moves, so its hosted
qualification, the release build and the build's install smoke run again at the new head
before the tag.
