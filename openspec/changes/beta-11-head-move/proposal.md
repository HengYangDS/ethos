# Proposal

## Why

The release head of 0.2.0-beta.11 was frozen on 2026-11-16 and its entry lists twelve known open
defects. Seven more were measured after the freeze, each confirmed at that head on 2026-11-17
with the head's own product code. The owner decided on 2026-11-16 that an entry states its known
defects before the tag, even at the cost of a new release head, and on 2026-11-17 that the head
moves once more, after the cut of 2026-11-19, with the whole release chain run again before the
owner is asked for the tag. A second answer of the same day put one product repair into that
move: the regression below.

What was measured at the release head, and how:

- Under Python 3.12 and 3.13 the apply of record retirement defers every batch while any process
  on the host has a long command line. The head's own tests: 15 failures on each.
- Under Python 3.12 a command that passes its time bound reports a bound a little below the
  declared one. The head's own test fails on 3.12.
- `ethos lane prewrite --patch` answers wrongly for five kinds of patch, measured through the
  patch admission with eight ordinary patches: it admits a move that is requested by its target
  alone, content left at the null path, and a new symbolic link; it reads the deletion of an
  empty file as an edit; it refuses the creation of an empty file, and a request for an entry
  that text follows. The commit hooks judge the staged tree: measured, they refuse the move and
  the null-path content and read the empty file's deletion rightly. They admit a staged link,
  in every release.
- On Windows the quality gates of a repository with many code files fail to start a Git
  process, and text handed to a native tool on standard input arrives with changed line ends.
  Read in the code at the head and measured by the first hosted Windows results of the batch.
- The regression: since this release's own fix on vendored and generated paths, the selection
  of authored files follows the local attributes file of the Git directory, which no proof
  binds. One line there turned the prose gate's answer for a committed document with two
  misspellings from block to pass, and the source binding stayed true. The predecessor blocks in
  every state. On the releasing host, 0 of 31 governed checkouts hold such a line.

Each of the first seven is repaired in the batch of 0.2.0-beta.12, which is reviewed and has
not landed.

## What Changes

Decided by the owner:

- One move of the release head after the cut of 2026-11-19. Its lane holds the entry's new items
  and the repair of the regression; one proof, one landing, and the whole chain before the
  owner is asked for the tag of 2026-11-21.
- The regression is repaired, not listed: the authored selection takes no mark from the Git
  directory's local attributes file. The repair is prepared outside the lanes; the way that the
  preparation's study measured as right in every state reads the marks through an empty Git
  directory of its own. The entry's Fixed item on vendored and generated paths gains one
  sentence. The older readers of Git attributes keep their answers; they are the subject of
  `local-git-state-binding`.
- The entry's list of known open defects gains the seven, each with what to do until a release
  repairs it, as measured: run ETHOS on Python 3.14 for the retirement; read a time bound from
  the configuration; for a move, content at the null path and an empty file's deletion the
  commit hooks judge the staged tree; end a patch at its last entry; and no step is known for a
  symbolic link.

Open, the owner's, asked on 2026-11-17:

- Whether the move carries the whole batch of 0.2.0-beta.12 and so repairs the seven instead of
  listing them.
- Whether it carries the repair of the deletion that `unsearchable-path-absence` states for
  Python 3.14.
- The entry's heading says that no known defect is in a blocking class. The two Windows items
  stop a gate there, and the entry already names the Windows adopter journey as not qualified;
  the lead reads them under that journey. The wrong admissions admit a write and no proof.

Not measured: advice for an empty file's creation, a whole proof with a local attributes line,
and anything on Windows by the release lead.

Not breaking: the entry is text, and the repair returns the predecessor's answer.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. The repair's delta arrives
with its Change.

## Impact

`CHANGELOG.md` at the release head, the selection of authored files and the release chain. The
measurements and the drafted items are local to the releasing checkout until the move's Change
opens from the accepted branch.

Owner: the release lead. Next action: freeze the items at the cut and open the move's Change
from the accepted branch, or fold both into the batch if the owner so decides. Read again: at
the cut of 2026-11-19.
