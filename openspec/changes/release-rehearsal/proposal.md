# Proposal

## Why

Five steps of an ETHOS release first run on a hosted runner when its signed tag exists: the
release build on each of five platforms, the assembly of the assets, their attestation and
publication, the binary scan and the adopter journey. The archived `release-step-coverage` design
moved one step, the inventory of a platform's archive, into every commit run, and named the
rehearsal of the others as a separate Change. The archived `rc-plan` design gives that Change:
appendix B.1 describes the rehearsal, B.2 its suites and time spans, and B.8 lists it as item 6,
`release-rehearsal`: B.1's jobs, modes, table, layout check and receipt. Its Family 7 orders the
row as B6, after `hermetic-journey` (B2), `release-predecessors` (B3) and `full-suite-legs` (B4),
which the batch of 0.2.0-beta.12 holds. The archived `rc-scope-plan` design places the row in the
batch of 0.2.0-beta.13, "the first rehearsed release", and DR-0029 records that cutting the
rehearsal and its admission was not taken.

What a rehearsal would have changed, read from the changelog and the archived release Changes
for 0.2.0-beta.6 to 0.2.0-beta.11:

- The hosted journey of 0.2.0-beta.6 failed on two hosts at the retained adopter's repair. The
  archived `retained-repair-scope` proposal says why: the real repair first ran against the real
  fixture at tag time. A journey before the tag would have met it.
- The release-only cases of the package acceptance run in a release build's install smoke, so
  no hosted leg runs them before a tag. The archived `release-trust-repairs` design says so for
  the cases that 0.2.0-beta.11 adds.
- Those sources record no other failed release run in that window. One is known from the
  releasing host's own record: the release run of 0.2.0-beta.8 lost three legs to the forge's
  artifact service and passed on its second attempt. No rehearsal reaches such a failure.

## What Changes

- The hosted workflow gains one dispatch input, `rehearse_head`. A dispatch that names the head
  of its ref qualifies that commit as a batch-head dispatch does, and also rehearses its release.
- `rehearsal-platforms` builds and qualifies the release wheel on the five declared release
  platforms with release identity, from the same declaration as the release legs.
- A rehearsal build is admitted without a tag: the checkout is clean at the named commit, that
  commit's signature passes the bound commit trust, its committed version has no tag and its
  changelog entry passes the release tag policy.
- `rehearsal-assets` runs the release's assembler in a job that holds no permission to attest or
  publish, and keeps the checksum file, the Mise declaration, the notes and the list of
  platforms left out.
- `rehearsal-journey` runs the adopter journey on each declared host: the candidate from the
  run's own assembly, installed offline, and each predecessor through its exact pin. The
  predecessors are the releases that the release binding records at the head.
- `release-rehearsal` gives the rehearsal one verdict: one expression over the jobs it needs. It
  writes no receipt: the bound receipt follows 0.2.0
  ([DR-0035](../../../docs/decisions/dr-0035-release-candidate-gate-scope.md), Waiver 4).
- The release guide's fourth step names the rehearsal dispatch for a release head.

Not breaking: no existing input, job name, artifact or session argument changes, and the four
jobs of a release run generate the same text. A governed repository has no such workflow and
meets no new rule.

Out of scope: the reading of a rehearsal by the product, its opt-in and any refusal, which are
`rehearsal-admission`; a journey that follows a pin to the candidate and lands, which the product
admits only for a published release (design decision 7); the golden paths, whose driver is
`golden-path-journey`; a Homebrew leg, which DR-0029 takes out of 0.2.0; a pre-tag binary scan;
the attestation and the publication themselves, and the candidate's own pin, which need a
published release.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: ADDED `A release head is rehearsed on hosted runners before its tag`, `A
rehearsal build carries release identity before the tag` and `A rehearsal's journey installs the
run's own assembly`.

## Impact

`.config/ci/pipeline.cue` and the workflow generated from it; `tools/ci/delivery/pipeline.py` and
`tools/ci/sessions.py` (the admission and its argument); `tools/ci/delivery/acceptance/journey.py`
and `acquisition.py` (the assembly as a source);
the model's tests under `tests/architecture/ci/` and the delivery tests;
`docs/guides/release-and-publication.md`; `CHANGELOG.md`; the distribution specification through
this Change's delta. No product module changes.

Measured on a spike in a scratch clone and not handed in: the model gains 209 lines and loses 50,
and the generated workflow grows from 692 to 923 lines. A linted sketch of the admission measures
34.5 tools line-equivalents. The built patch, measured by the source-budget report on a clone of
`dev` `3c6260017` on 2026-11-25: 104 tools and 340 test line-equivalents, no product line,
against a planned 240 and 190. The second forge's pipeline does not change.
