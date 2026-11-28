# Design

## Context

See the [proposal](proposal.md) and the [delta](specs/distribution/spec.md). "The plan" is
`openspec/changes/archive/2026-11-07-rc-plan/design.md`, appendix B.1; "the model" is
`.config/ci/pipeline.cue`.

Read at the base:

- A dispatch with `qualify_head` qualifies one exact commit: its commit-scoped jobs run only at
  that commit, the full conformance tier and the suite legs join the run, and the aggregate
  `hosted checks` fails at any other commit (the model's `headMatches`, `fullRun` and the
  aggregate's second step).
- `release-platforms` and `release-publish` run for a dispatch from `main` that names a signed
  tag; `release-binary-scan` and `release-journey` follow the publication, or run alone for a
  published tag. A hosted release build is admitted by that tag alone
  (`_require_signed_release_tag` in `tools/ci/delivery/pipeline.py`); the releasing host has a
  second admission, the accepted source with its local proof.
- The assembler (`assemble` in `tools/ci/delivery/release_assets.py`) writes the assets, the
  checksum file, the Mise declaration, the notes and `left-out.json`. Attesting and publishing
  are two other steps of the publication job.
- The journey qualifies a published tag in two stages. Acquisition downloads the release from
  the forge, proves each pin and writes a manifest; qualification reads the manifest alone and
  installs each archive offline from a `file://` table.
- A transition follows the accepted branch's pin only in its GitHub form, and only when the
  accepted lock's entry for the platform binds the release: by the attestation's provenance for
  every release from 0.2.0-alpha.29 on (`follow_accepted_pin` and `_binds` in
  `src/ethos/adapters/repo/runtime/pin_selection.py`). A probe of the pin module in a scratch
  clone gave an attested class for a version that has no tag, read the local table as the older
  form, which holds no pin key, and found that a lock entry with a checksum and no provenance
  binds nothing for such a version.

Measured in a scratch clone at the base, and reverted:

- A spike added the input, one shared declaration of a release leg and four jobs to the model.
  `git diff --numstat` gives 209 added and 50 removed model lines and 240 added and 9 removed
  workflow lines, 692 to 923. By job the generated lines are 87, 27, 73 and 39.
- `tools.ci.ci_projection.check_templates`, the projection's byte comparison, and
  `check_workflow`, the Actions check and the shell check of each run step, exit 0 on the
  spike; 98 shell steps carry no diagnostic. The second forge's pipeline and the generated
  text of the four release jobs are byte-identical to the base's (`cmp` on each job's block).
- The fifteen model test modules ran on the spike, one a run. Eleven pass. Four fail in six
  tests, each an equality of the head rule, the full tier or the aggregate's expression with a
  fixed text.
- A sketch of the admission in `pipeline.py` and `sessions.py` passes the linter and measures
  34.5 tools line-equivalents by the product's measure. Its request parser answered one call;
  the admission itself never ran.
- One runtime archive of a release build of 0.2.0-beta.11 on the releasing host is 273,019,342
  bytes.
- Tests measure 1.8 to 2.7 times their product module for three neighbors of the batch: 232.0
  for the hosted reader's 130.9, 249.9 for the release acceptance's 94.0 and 118.2 for the
  predecessor set's 65.6 line-equivalents.

## Goals / Non-Goals

Goals:

- The release build on every declared platform, the assembly and the journey run on hosted
  runners at the release head before its tag exists.
- A rehearsal can publish nothing and attest nothing, by its permissions.
- A change to a release leg changes its rehearsal with it.
- The rehearsal has one verdict, also when a leg failed.

Non-Goals:

- Reading a rehearsal into the product, recording it or refusing a tag without it:
  `rehearsal-admission`.
- Equal bytes between a rehearsal build and the release build of the same head. The plan lists
  reproducible bytes as unproved, and nothing here compares them.
- The attestation, the publication, the binary scan and the candidate's own pin. Each needs a
  published release and still first runs at the tag.
- A rehearsal for a governed repository. The jobs are this repository's own pipeline.
- A time budget. `release-time-budget` sets it from the first rehearsed release.

## Decisions

1. **A rehearsal is a dispatch that names its head, and it is a full run.**
   - **Rests on:** the base's `qualify_head` rule and the suite legs' condition, read in the
     model; the spike, in which `rehearse_head` joins `headMatches` and `fullRun` and the model
     compiles.
   - **Considered:** a second workflow file, which gives the release legs a second owner; a job
     `rehearsal-suite` of its own, as the plan names, which repeats two suite legs of 51 and 60
     minutes of test time (their JUnit reports, read on 2026-11-17) in the same run; and a
     dispatch from `main` after publication, which rehearses nothing before the tag.
   - **Chosen because:** one run qualifies and rehearses the head, so the release lane
     dispatches once where the guide's fourth step dispatches today. The cost: one failed
     conformance leg fails the rehearsal, and the emulated Windows legs bound its time.
   - **Applies to:** the GitHub workflow; the second forge's qualification of the head stays
     as the guide states it. The plan's `rehearsal-suite` is the suite legs of the same run
     and no job of that name. A batch head that is no release head keeps `qualify_head`. The
     guide names the release lane's proposal ref, after the lane's proof and before the
     landing, as the place of the dispatch, so that a failed candidate does not reach the
     accepted branch; the dispatch itself runs on any ref whose head it names. A rehearsal
     stands for one commit: a release head that moves is rehearsed again. A dispatch that
     also names a release, a journey, a scan or the supply image rehearses nothing: its
     rehearsal jobs skip and its verdict job fails, so two jobs never upload one artifact
     name. The spike did not hold this last rule.
2. **No script receives the dispatch's value.**
   - **Rests on:** the base, where the release run writes `release_head` and `release_tag` into
     script text and the journey passes `journey_previous` through `env`, as its test requires;
     the spike, whose rehearsal steps name the runner's own commit.
   - **Considered:** `env` in each step, the plan's words, which is safe and adds a variable to
     four jobs; and the release run's form, where a dispatch's text becomes shell text.
   - **Chosen because:** a rehearsal job runs only when the input equals the runner's commit, so
     that commit's name carries the same value and no step holds user text. A test refuses a
     rehearsal step that contains an input expression.
   - **Applies to:** the four rehearsal jobs. The input appears in job conditions and in the
     `env` entry of `hosted checks` that tests the head. The release run's own interpolations
     are the plan's `release-provenance` row.
3. **A rehearsal leg and a release leg are one declaration.**
   - **Rests on:** the spike: one declaration takes the job's condition, its checkout and its
     arguments, and the release job that it generates is byte-identical to the base's.
   - **Considered:** a copied job, 48 model lines a second time, which lets a rehearsal drift
     from the release it predicts; and a matrix dimension on the release job, which renames the
     release run's jobs.
   - **Chosen because:** a change to a release leg's steps changes both jobs or neither. The
     release audit comes with it: the build and the install smoke run the production-release
     audit whenever a head is named, so an advisory blocks a rehearsal leg as it blocks a
     release leg.
   - **Applies to:** `rehearsal-platforms`, the five legs with their required and optional
     marks. The assembly and the journey share the model's host lists and supply steps; their
     own steps differ from the release's, which publishes and reads a published tag.
4. **A rehearsal build carries release identity, admitted by its head's own signature.**
   - **Rests on:** `_release_source_identity`, which checks the exact head and a clean tree
     before either admission; the commit trust that each release leg binds; the release tag
     policy's checks of the committed version and the curated entry; and the sketch's size.
   - **Considered:** a development build, which the release-only cases of the package acceptance
     never see and the plan rules out by asking for release identity; a scratch tag, which
     publishes a ref that must be deleted; and a marked identity, a third kind of build that no
     release ships.
   - **Chosen because:** the rehearsal exists to run the release path, and the identity of a
     head's rehearsal build is the identity that its tag will admit. The new refusals belong to
     the new mode: `release_rehearsal_head_untrusted` for a head whose signature the bound trust
     does not pass, `release_rehearsal_tag_exists:v<version>`, and the entry's own errors. A
     request that carries both the rehearsal mark and a tag is refused as invalid.
   - **Applies to:** the `build` and `install_smoke` sessions when a release request also
     carries `--rehearse`. It accepts, attests and publishes nothing. It does not require the
     head to be on a release lane: any signed head whose version is untagged and whose entry
     is valid can be rehearsed. A head whose version already has a tag cannot: its build would
     carry a released version's identity from another commit. Outside a rehearsal the signed
     tag stays the only admission of a hosted release build.
5. **The assembly is the release's assembler in a job that cannot publish.**
   - **Rests on:** the reading of `assemble` in the Context; the spike, whose generated step
     calls it unchanged with the committed version as its tag; and the workflow's default
     permission, which is to read contents.
   - **Considered:** a rehearsal flag on the assembler, which has no behavior to switch; and the
     publication job with a dry-run input, which keeps three write permissions in a job that
     must not publish.
   - **Chosen because:** the same code admits the same legs, and what keeps a rehearsal from
     publishing is a permission that the job does not hold. A test refuses a rehearsal job that
     declares any permission beyond reading contents and attestations.
   - **Applies to:** `rehearsal-assets`. It waits for every leg, as the publication job does,
     so `left-out.json` names an optional platform as the release would. It uploads the checksum
     file, the declaration, the notes and `left-out.json`, and no second copy of the archives:
     five of them are about 1.4 GB if each is as large as the one measured, and each leg's own
     upload already holds its archive. The spike uploaded the whole output; the design does
     not.
6. **The journey qualifies the run's own assembly and takes its predecessors from the record.**
   - **Rests on:** decision 5 of `hermetic-journey`, which made the manifest a file so that this
     row can supply its own archives; `install_archive`, which installs offline from a `file://`
     table with the digest it is given; the non-goal of `release-predecessors` that leaves the
     rendering of the record to this row; and a read of the base's binding, which records no
     set.
   - **Considered:** a dispatch input for the predecessors, as `journey_previous` is, which a
     person fills and the plan retires; and a pin of the candidate, which cannot be locked
     before a release exists.
   - **Chosen because:** qualification does not change. Acquisition gains a second source for
     the subject: its platform's archive from the leg's upload, admitted only when its digest
     is the one that the assembly's checksum file lists for the published name. Each
     predecessor is acquired as today, through its exact pin and verified by its class, for the
     leg's own platform. The predecessors are the releases of `[release.upgrade_from]` at the
     head; a head that records none takes the first earlier published changelog entry, as the
     journey does today, and the receipt says which source it used.
   - **Applies to:** the three declared journey hosts. The manifest names the subject's class as
     `rehearsed`, a value of the journey tool and not of the pin module. The candidate's
     offline install and each predecessor's pin install pass the two layout checks that exist,
     one console entry and one runtime generation, so the plan's equal-layout clause needs no
     new code. Not rehearsed: the subject's own pin, its attestation and the two rebound-lock
     refusals.
7. **A rehearsal follows no pin to the candidate and lands nothing.**
   - **Rests on:** the pin follower's rule and the probe in the Context: before a release is
     published and attested, no lock that Mise writes binds its pin, and the product answers
     `runtime_pin_unattested`; the local table that a rehearsal installs from is no pin at all.
     Decision 2 of `hermetic-journey`: a journey child finds no Mise on its path. The design of
     `rollback-after-repair`: the product finds Mise on the path alone, and the plan's steps
     need a helper that lands, where the acceptance package probes `land` and never lands
     (`grep -n '"land"' tools/ci/delivery/acceptance/*.py`). The release lead's ruling of
     2026-11-17 on that row, which sends the journey that follows a pin and lands to this
     design.
   - **Considered:** a lock entry that the harness writes with the provenance word, which shows
     the product following bytes that nothing attested; keeping acquisition's Mise home and
     path for qualification, which reopens decisions 2 and 4 of `hermetic-journey` and still
     locks no candidate; and the plan's four steps inside the rehearsal, which that design
     estimates at 350 to 450 tools and 250 to 350 test line-equivalents.
   - **Chosen because:** the product itself refuses the step before publication, so a journey
     that follows a pin to its subject and lands can run only on a published subject. It is the
     published journey's, where acquisition holds Mise and the forge. The rehearsal runs what
     the journey runs offline: the upgrade and the rollback by name, and the rollback after the
     repair once `rollback-after-repair` lands its first slice.
   - **Applies to:** the plan's "restore-then-rollback" clause, owned by `rollback-after-repair`
     with the pinned adopters of `journey-fixtures`, and read again at the cut of 0.2.0-beta.14,
     when published releases ship the receipt; the golden paths, owned by `golden-path-journey`
     and read again when its driver lands; a Homebrew leg, which DR-0029 takes out of 0.2.0 and
     which is read again after it.
8. **One job gives the rehearsal's verdict.**
   - **Rests on:** `hosted checks`, which tests one expression over the results of the jobs it
     needs, so that a job that wrongly skips fails it; the spike's aggregate.
   - **Considered:** the run's own conclusion, which is success when a rehearsal job is skipped
     by a wrong condition.
   - **Chosen because:** a reader needs one name. `release-rehearsal` runs whenever the dispatch
     names a head, also at another commit, where the rehearsal jobs skip and it fails.
   - **Applies to:** `hosted checks`, which holds the required suite legs; the three required
     platforms, through the legs' own optional mark; the assembly; and each journey host.
9. **The rehearsal writes no receipt in this Change.**
   - **Rests on:** [DR-0035](../../../../docs/decisions/dr-0035-release-candidate-gate-scope.md),
     Waiver 4, which places the bound receipt, its Attestation and its command after 0.2.0; and
     decision 5 of `hosted-observation`: a record without a reader is unproved.
   - **Considered:** building the receipt's writer here, estimated at 110 to 160 tools and 130 to
     200 test line-equivalents, for a file that no reader of 0.2.0 takes.
   - **Chosen because:** the waiver names what stands in its place: a rehearsal before each tag,
     a task of each release Change that reads the verdict, and a second session that reads the
     run. The verdict job is therefore one step that tests one expression, as `hosted checks`
     does, and each leg keeps the artifacts it uploads today.
   - **Applies to:** the verdict job. The receipt, with its reader, belongs to the row that
     builds the admission's record after 0.2.0; `rehearsal-admission` reads the verdict job.
10. **The model's change is reviewed through its projection, and tests pin what must hold.**
    - **Rests on:** the release lead's note of 2026-11-17 that the batch's model review tool
      does not read CUE; the projection check, which compares the compiled bytes with the
      committed workflow; and the workflow validation of the spike.
    - **Considered:** a reading of the model by eye alone; and a reviewer that reads CUE, which
      the supply does not hold.
    - **Chosen because:** every model line reaches a reader as generated workflow text. That
      diff is what is reviewed, and three tests hold the rest: the four release jobs generate
      the text they generated before; a rehearsal leg's steps equal a release leg's but for the
      checkout and the two argument strings; and no rehearsal job holds a write permission or
      an input expression in a step.
    - **Applies to:** this Change's model edits and the six tests that compare a fixed text of
      the head rule, the tier or the aggregate, which change with it. Tests pin text and not
      behavior: the first end-to-end run is a dispatch.

## Risks / Trade-offs

- No job of this Change has run. The first end-to-end run is one dispatch of the hosted workflow
  on a proposal ref with `rehearse_head` set to that ref's head. It needs a head whose committed
  version has no tag and whose entry is valid. The accepted branch holds such a head only from
  a release Change's landing to its tag: at the base that is the version of 0.2.0-beta.11
  (`changelog_errors` returns nothing for it, and the clone holds no tag of it), until its tag.
  After that the first run is the rehearsal of the next release head itself, or a scratch head
  that moves the version and is never landed.
- The release that first carries this Change can be rehearsed if a dispatch runs the workflow
  of its ref with that ref's inputs: a release lane whose head holds the rehearsal jobs then
  rehearses that head. Dispatches of the batch before this one ran new jobs from a proposal
  ref; whether the forge accepts an input that the default branch's workflow does not declare
  is not verified, and the first dispatch shows it.
- The rehearsal's time is an estimate from recorded job times, not a measurement: the emulated
  Windows leg took a median of 74.3 and at most 86.0 minutes over 19 successful release legs
  (the releasing host's reading of the forge's job history on 2026-11-14, the source of the
  model's timeout table), the assembly less than the publication job's 1.8, and a journey leg
  254 to 271 seconds with one predecessor on 2026-11-17, and at most 24.5 minutes in the same
  history, with several predecessors and before the journey's two stages. That gives 81
  minutes from the medians and 113 from the longest job of each kind, against the plan's 110
  to 125, without the time a job waits for a runner. The qualification it replaces already
  waits for an emulated conformance leg of 74 to 81 minutes.
- A rehearsal is one more run that can meet a forge outage, as one release run did.
- Whether a landing keeps the lane's head as the accepted head was not read for this design.
  Where it does not, the rehearsal is dispatched for the accepted head after the landing, as
  the guide's fourth step qualifies it today, and a failed candidate is then already on the
  accepted branch.
- A release head that moves after its rehearsal costs another run. The head of 0.2.0-beta.11
  moved once for its entry alone (the archived `beta-11-known-defects` Change).
- A passed rehearsal proves the path for bytes built at that time. The release run builds again.
- Anyone who may dispatch the workflow can make a runner build release-identity bytes of a
  signed, untagged head. They are uploaded as run artifacts for the declared retention and are
  neither attested nor published.
- The built patch measures 104 tools and 340 test line-equivalents; the plan had 240 tools and
  190 tests. The tests fit under the test ceiling only with the cleanup that enters the same
  batch, which is measured stacked at each cut.
- The accepted scenario for a hosted release build says that only the signed tag admits release
  identity. `release-acceptance` modifies that requirement in the batch before this one, so
  this Change's delta adds a requirement and leaves the restatement of that scenario to the
  lane, after that Change is archived.
- The journey's new source reads files by path. The product supports three interpreters, and a
  path predicate behaved differently on two of them in an earlier release, so its tests run on
  all three.
