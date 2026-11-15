# Proposal

## Why

The ten gate rows of 0.2.0-beta.11 are archived on `dev` under passed full proofs of the landed
trees, and the tag is due on 2026-11-21. A release's execution plan is the plan's rows; this
Change keeps the release's own steps, so that none waits in an archived follow-up.

- `adopt-pin` withdrew two tasks under DR-0016. The release build's install smoke is a step of
  this release. The form of the relock is decided, and `adopt-lock-directory` landed it.
- A model review read the whole diff of this release on 2026-11-15, product, tools and
  configuration, and returned 13 leads. A regression written first decided 12 of them, and each
  was real at least in part. Ten are repaired by Changes of this release's lane, which land with
  it: `host-ticket-release`, `adoption-pin-repairs`, `gate-provider-identity` and
  `release-trust-repairs`. Two are carried forward: gap codes that only a family registers, in
  the draft `gap-code-literals`, and a version accepted again across its checksum binding, whose
  transition nothing calls in this release, in the follow-up of `release-trust-repairs`. The
  thirteenth, on the journey's negative cases, was read and not tested, and is a known open
  defect of the entry.
- The same review then read the lane's own diff in parts, and each of its comments has a verdict
  beside the lane's proof record.
- The pre-tag copies run is read by a session other than the batch's authors'. On 2026-11-15 its
  preview covered 13 of 13 readable trees, and its executed half ran 9 of them: 8 passed in full,
  and one ran 8 of its 10 checks, because a gate of that tree asks for the runtime's own wheel
  and a source build names none. The repairs change product code after that reading, so the
  reader repeats it on the release head's candidate before the tag.
- The owner decided on 2026-11-15, as relayed by the adoption session, that the 14-day artifact
  retention ships in this release with its corrected entry.
- The batch carried three off-gate rows against the rule of one a week: the supply move, the
  structure design and the artifact retention. They were in the stack before the rule was set. The
  owner accepted the excess once on 2026-11-15; from 0.2.0-beta.12 a batch carries one.
- Three more items outside the gate's rows landed before the tag. Two did by the owner's word of
  2026-11-15: the direction design, and DR-0029, which the committee had placed in
  0.2.0-beta.12; that batch's off-gate slot is free again. The third is the test budget step
  under DR-0028, which the rows of the next batch need and which changes no product code.

## What Changes

- `VERSION` moves to `0.2.0-beta.11`.
- The `[Unreleased]` entry becomes the `0.2.0-beta.11` entry. It names the release that its
  journey upgrades from, the journeys this beta does not qualify, the law by state, the count
  for each gap code of the copies run, every advisory that the audit reports and the known open
  defects a user can meet. Each Breaking entry names its repair and its order.
- After the landing, by the release guide: the release build's install smoke, the copies run on
  the candidate that this lane's proof keeps, the qualification of the release head on both
  forges, the tag, the build and the journey. The tasks' follow-up section lists them.
- The weekly page's first edition is read from `dev` by a session other than the authors'. Its
  measure of off-gate rows states the six items of this batch and the authority of each. The
  reader's count of subjects on 2026-11-15 is 10.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release entry changes no requirement, so `skip_specs: true` applies.

## Impact

`VERSION` and `CHANGELOG.md`. No row lands in this Change.
