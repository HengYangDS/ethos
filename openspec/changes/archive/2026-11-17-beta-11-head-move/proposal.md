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

Decided by the owner on 2026-11-17, the last answer that evening:

- The one move of the release head carries the whole batch of 0.2.0-beta.12: its nine rows of
  the gate, reviewed and green on both forges, with the repairs below. The seven defects above
  are then repaired by the release and are not listed. One lane, one proof, one landing, and
  the whole release chain before the owner is asked for the tag of 2026-11-21. This changes
  the earlier answer of the same day, by which the move held the entry alone.
- The way back, bound by the release lead's words on the page: if the batch's whole
  verification has not passed by 2026-11-19 12:00, the move holds the entry's seven items and
  the repair of the regression alone, as first decided, and the batch lands after the tag.
- The regression is repaired, not listed: the authored selection takes no mark from the Git
  directory's local attributes file. The way that the preparation's study measured as right in
  every state reads the marks through an empty Git directory of its own, and its last form
  reads them against the tree that the source binding's owner builds
  (`authored-selection-local-attributes`). The entry's Fixed item on vendored and generated
  paths gains its sentences. The older readers of Git attributes keep their answers; they are
  the subject of `local-git-state-binding`.
- The host store's reader of a consumer's state asks the host for a status where it asked a
  path question, each state measured on three interpreters with a case. A selector below a
  directory that may not be searched reads `unknown`: under Python 3.14 it read as a selector
  that names nothing, and the cleanup deleted an installation that its repository still
  selected. A consumer whose path is a link that names nothing, or a file, reads `unknown`: on
  every interpreter it read `released` and lost its record and installation. A consumer below
  a directory that may not be searched reads `unknown`: under Python 3.12 and 3.13 it ended
  the whole cleanup with an error. A second reader and four model reviews found these states
  one after another.
- One advisory is accepted for one artifact. GHSA-fc5q-39xc-vjpf names every picomatch release
  and has no fix, and since 2026-11-17 the dependency audit blocks the picomatch 2.3.2 of this
  repository's lock, so no head passes a proof. The owner accepted that artifact on 2026-11-18,
  for this repository's lock, until 2026-12-02.
- A standing rule for the release lead: a defect found before a tag is repaired without a
  separate ask, and reported on a page afterwards, when its repair changes one reader and adds
  no refusal, passes on the three supported Python versions, is reviewed, and the whole release
  chain ends before the page that asks for the tag. Where one of the four does not hold, the
  defect is written into the entry and the owner is asked. The tag stays the owner's word. The
  rule's place in a tracked page is shown to the owner with the Change that carries it.

Read again for the move:

- The entry's twelve listed defects, against the lane head: three are repaired by rows of the
  batch and leave the list, nine stay, and the accepted advisory joins them.
- The entry's heading, which says that no known defect is in a blocking class: it holds for
  the ten.
- Left in the consumer reader and not repaired by the move: under Python 3.12 a selector that
  names a local runtime which links to itself ends the whole cleanup with an error
  (`unsearchable-path-absence`).

Not measured: a whole proof with a local attributes line, and anything on Windows by the
release lead.

Not breaking: the repairs return the predecessor's answer or keep what was deleted.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None: no requirement's words change, by decision 5 of the design, so `skip_specs: true`
applies. The regression's delta is in `authored-selection-local-attributes`.

## Impact

`CHANGELOG.md`, the host store's reader of a consumer's state, the selector's reader, the
dependency audit's policy and the release chain.

Owner: the release lead. Next action: the full proof of the archived head, then the copies run
on its candidate. Read again: 2026-11-19 12:00, the hour of the way back.
