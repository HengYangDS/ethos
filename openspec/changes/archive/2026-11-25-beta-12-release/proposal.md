# Proposal

## Why

The nine gate rows of 0.2.0-beta.12 are archived on `dev` under passed full proofs of the landed
trees, and DR-0029 sets the tag for 2026-11-28. A release's execution plan is the plan's rows; this
Change keeps the release's own steps, so that none waits in an archived follow-up.

- `dev` still holds the version of the previous release. An accepted requirement binds a release
  tag to the `VERSION` of its tree, so the tag needs a tree whose version is 0.2.0-beta.12.
- Eighteen Changes were archived on `dev` since the previous tag, and the known-defect entries
  landed after them. The `[Unreleased]` entry was written lane by lane; a reader held every landed
  Change against it on 2026-11-26 and named what a user can observe that it does not yet state.
- This is the first release entry written beside `defects/`. That directory's design gives the
  release's Change two duties: it fills `fixed_in` for the entries closed since the previous tag
  and fills an empty `since` where the defect ships first with this release. Eight entries are
  closed and one has an empty `since`.
- The copies run is read by a session other than the batch's authors'. On the candidate built at
  the last product change it proved the governed repositories that the releasing host reads:
  twelve passed in full, one is refused before execution on two gaps of its own tree that the
  previous release reads the same, and one, which has no accepted branch, is evidence only. After
  the known-defect entries landed, the same reader's previews of all fourteen were equal to those
  before it. The release head moves the version, so the reader reads it again before the tag.
- An accepted requirement has the release binding record each release that the release
  upgrades from, and the release guide records it in the release Change. The binding holds no
  such table: 0.2.0-beta.11 was tagged without it, and `ethos lane upgrade-from` blocks with
  `release_upgrade_from_empty`.
- The previous entry printed a total of the paradigm's obligations, 47. No file enumerates
  them, and the count cannot be derived again.
- Seven of the Changes open on `dev` have landed parts that the entry states. Six have work
  left. The seventh, `known-defect-entries`, landed whole on 2026-11-25 with none of its
  five tasks recorded, so the tree under the tag would say that none of its work is done.
- The owner decided on 2026-11-25 that ETHOS ends its support for Windows. The removal lands
  after this tag, so this is the last entry that can give notice of it before it happens.

## What Changes

- `VERSION` moves to `0.2.0-beta.12`.
- The `[Unreleased]` entry becomes the `0.2.0-beta.12` entry, completed from the landed Changes. It
  names the release that its journey upgrades from, the journeys this beta does not qualify, the
  law by state, the result of the copies run, and where the known open defects are kept. It
  prints no total of obligations, and it gives notice that support for Windows ends.
- `.ethos/release.toml` gains `[release.upgrade_from]` with the releases that
  `ethos lane upgrade-from` derives for 0.2.0-beta.12. The test that pinned the binding's
  release table to the mirror alone now holds that the table records the release before the
  committed one.
- The Change `known-defect-entries` has its task states recorded from its evidence and is
  archived.
- The known open defects are no longer copied into the entry as a list. The entry names
  `defects/`, the count of open entries at its head and the one divergence that the owner asked to
  see stated in this release's entry.
- Under `defects/`, the eight closed entries gain `fixed_in = "v0.2.0-beta.12"`, and the one entry
  with an empty `since` gains `since = "v0.2.0-beta.12"`. No open entry is edited otherwise.
- After the landing, by the release guide: the reader's pass on the release head, the
  qualification of the release head on both Forges, the tag, the build and the journey. The tasks'
  follow-up section lists them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release entry changes no requirement, so `skip_specs: true` applies.

## Impact

`VERSION`, `CHANGELOG.md`, the release binding, nine files under `defects/` and the Change
`known-defect-entries`, which moves to the archive, and one test of the release binding. No row
lands in this Change, and no product code changes.
