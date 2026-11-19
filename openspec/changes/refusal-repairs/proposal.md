# Proposal

## Why

Five results say less than the reader needs, or more than they prove. Each was measured by the
release lane or by a governed repository's session under 0.2.0-beta.10:

- The link gate prints an exit status and reports `gate_failed`. The redirecting URLs sit in the
  proof's payload as a string inside another report's output.
- The staged size check reports one file for each refusal: eight files over the ceiling cost
  eight rounds.
- The audit's repair text for a version source proposes the manifest's PEP 440 version for
  `VERSION`, which the release then refuses as no semantic version.
- A document's front matter counts toward the document ceiling, 5 to 7 lines for each document.
- The hosted journey's foreign-attestation case no longer isolates the attestation check. Mise
  refuses the lock entry that names another release's asset by its URL, before any attestation is
  read. The journey proves that foreign bytes are refused, and its docstring claims more.

## What Changes

The first slice is one class, which the owner named on 2026-11-17 as the one off-gate row of
0.2.0-beta.13: a check reports every finding that it computed. A check that has computed
several findings reports one, so each finding costs a run, and under a host queue each run
costs a wait. Measured by one governed repository's session under 0.2.0-beta.10 on 2026-11-17:
two gates went from never run to pass in three host tickets, 10,334 seconds in the queue and
974 seconds of slot, for four findings that one run had computed. Read in this product on the
same day: the evidence reader builds the whole list of unexercised files and of a static
report's findings and carries the first, the behavior gap returns one kind and no path, the
content reader stops at the first target that the tree does not deliver, and the staged size
check below is one more case. The bullets below stay as named remainders.

- The link gate's gap carries each redirecting URL and its target.
- The staged size check reports every file over the ceiling in one refusal.
- The version-source repair proposes a value that the release accepts.
- The document ceiling measures the body.
- The journey's docstring and the design sentence state what the case proves.
- A refused runtime selection whose refusal carries no next action, as for a damaged
  install, names its repair; `ethos adopt --select-runtime` repeats its own request there,
  which meets the same refusal (observed in `adoption-pin-repairs`).
- The repair text of `runtime_pin_unattested` names what the lock must record for the release's
  class. It speaks of an attestation also for a release that only a checksum binds, which
  `release-trust-repairs` began to refuse without a lock entry.
- To read, not measured yet: other denied placements that may refuse their own repair, as the
  write guard did before `denied-path-removal`: the audit's repair plans for tracked scripts, and
  denied generated homes.
- A proof's source-format gate result names the same next step as `ethos lane format --check`:
  the apply, the naming of a kept record, or the Git attribute that marks a path received.
- The shipped format policy drops `immutable_record_roots`, which `record-roots-one-owner` stopped
  reading. It leaves one release after that Change, when the runtime that judges this repository
  is built from a head that accepts the policy without it.
- A lane path that carries the local day is refused with `work_lane_path_not_canonical`, because
  a lane's directory carries the UTC day of its start. The expected path is in the result's data
  and in neither its message nor its next action; the refusal names it. Reported by one governed
  repository's session on 2026-11-16: on a host east of UTC the two days differ in the first
  hours of its day.
- `ethos lane start` with a name that carries a date is refused with `work_lane_name_dated`,
  and its next action is the start under the undated name without the `--base` that the
  refused command named. Followed as printed, it starts the lane from the candidate and not
  from the named commit. The next action keeps every argument that the request gave.
  Measured by the release lane on 2026-11-17 in a preview.
- A refused rename of a retained topic names `ethos lane repair-paradigm --apply --json` as its
  next action, which is the request that was just refused; under `--pin` it names the same
  apply with `--pin`. The rename's own report is the owner: its step names what removes the
  obstacle. A recovery that is itself refused (a stale binding, a foreign holder) reports
  `partial_transition` like an interrupted rename and is named the same apply; the report
  tells the two apart. Found by the model review of `adopter-bump` on 2026-11-16.
- Three readers of a caught refusal take its gaps from the error's text or from its outcome,
  which is empty for a refusal that carries none, so a block can read as a pass: the mutation
  proof, dependency acceptance and the readiness of a commit rebuild. `refused_gaps` never
  answers none; each reader moves to it with its own regression. The name it gives such a
  refusal is its class, which no registry row holds and no repair follows: it gets a
  registered code. Found by the same review. Read in the batch lane on 2026-11-16: 43 more
  lines of product code make a one-element list or tuple of the error's text, nearly all as a
  result's gaps, which keeps the first gap of a refusal that carries several; not each line
  was traced. The repair is one reader and a guard for the class, not a patch a line.
- The argv selection takes the next token as an option's value, also when that token is an
  option: `status --root --json` selects an operation, and the CLI refuses the same argv. A
  step derived from such an argv reads as live. Found while `environment-entry` was repaired.
- The documentation health report measures the documents it is handed. Called without the
  tracked documents it reads the registered ones alone, so a Change artifact above the document
  ceiling passes there and is refused by the gate, whose callers pass every tracked Markdown
  file. A reader of the report alone reads a pass. Reported by a governed repository's session
  on 2026-11-16; one caller in this product asks without them.
- The retirement of a proposal ref whose tip accepted history does not hold is refused in this
  repository with `signature_repair_source_coordinates_mismatch`, and its next action repeats
  the request. The question whether the tip is conserved walks the recorded signature repairs
  beneath accepted history, and the source commit of one record is no longer in the object
  store, so its validation fails as a mismatch of coordinates. The rule that such a ref leaves
  only while a Work Lane or a closed review retains its tip is never reached. Measured on
  2026-11-16 on the proposal ref of an abandoned lane. The same question is asked for absorbed
  proposals, for the retirement of an absorbed ref and for the admission of a ref move. Met again
  on 2026-11-19 on two proposal refs whose head a base refresh had rewritten: the refusal names
  coordinates where the source is absent, although the repair's creation already has a code for
  an unavailable source. Why the source can be absent, and how a repair keeps it, is the draft
  `repair-source-retention`.
- The release build's install smoke takes the one wheel under the release artifacts, which only
  the release build writes. Run without that build, it read a wheel that an earlier release
  build had left and refused with `hook_runtime_wheel_build_identity_invalid` (measured on the
  accepted root on 2026-11-16, on a wheel of an earlier layout). The refusal says that the wheel
  is not built from the requested head and names the release build as the next step.
- The preview of `ethos hook retire-records`, run from a build that the repository does not
  select, refuses with `record_retirement_runtime_unselected` and names no next step: the
  result's next action and its instruction are empty. Measured on the accepted root on
  2026-11-17. The refusal names the selected runtime's own console.
- A repair of the accepted specification tree is admitted for the worktree and refused at its
  commit. The worktree admission marks a profile's added metadata declaration and the move of a
  supporting file as repairs, each with a scope of its own while the tree holds other gaps. The
  staged admission, which `lane prewrite --target index` and the commit hook use, marks neither,
  so a commit passes only when its staged tree holds no gap of `openspec/specs` at all. Met by a
  governed repository's session under 0.2.0-beta.10 on 2026-11-19 and measured in a fixture on
  this lane's code the same day: the profile repair passes for the worktree and is blocked
  staged, and one commit that leaves no gap passes. Each admission names the same repairs.
- `ethos lane repair-signature` refuses a commit inside a Work Lane's unpublished range with
  `signature_repair_accepted_head_stale` and names its own apply as the next action; no command
  repairs an unsigned commit of a lane's own range. Measured by a governed repository's session
  on 2026-11-18 under 0.2.0-beta.10, on three such commits of one lane.
- The paradigm's commit grammar admits ten types and not `style`, which the Conventional Commits
  common set holds; the same session met eight signed commits of one lane refused for it. Why
  the type is absent is read before a change; the list is the one grammar of every governed
  repository, so adding to it is the owner's decision.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

Four checks' results and one docstring. Each narrows or clarifies a refusal, which the law freeze
admits; none adds a rule.

Owner: the release lead. Next action: the design and the measured patch of the first slice for
the batch of 0.2.0-beta.13; then each remainder as its own small Change, or as one when they
share a file. Read again: at the cut of 0.2.0-beta.14.
