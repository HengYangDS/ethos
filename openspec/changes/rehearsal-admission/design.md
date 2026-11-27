# Design

## Context

See the [proposal](proposal.md) and the deltas. "The plan" is
`openspec/changes/archive/2026-11-07-rc-plan/design.md`, appendix B.1; "the verdict job" is the
job `release rehearsal` that `release-rehearsal` adds to the hosted workflow.

Read at the base:

- `observe_hosted_runs` lists the runs of one commit on a peer with one bounded call and reads
  the jobs of a run only when it failed or still runs
  (`src/ethos/adapters/mutation/publication/hosted_runs.py`). Its listing asks for a run's
  identity, commit, status and conclusion. It asks for no creation time and no event, and no
  product module downloads a run's artifact (`grep -rn '"download"' src/ethos` finds no forge
  call).
- `hosted_observation` has three callers (`grep -rn "hosted_observation(" src/ethos/application`):
  the explicit observation, the landing preview and the probe of a release ref. It is read each
  time and stored nowhere, and the explicit observation's verdict comes from `observation_gaps`
  alone.
- The release table's key set is `mirror` and `upgrade_from`. A probe in a scratch clone gave,
  for a binding that declares `[release.rehearsal] peer = "github"`, one `release-binding` gap
  whose obligation is armed and for which the repair plans no edit.
- `land --release` reads the proof of its head and no forge (`_observe` in
  `src/ethos/adapters/mutation/accepted/release.py`, a module of 438 of 500 effective
  lines). `src/ethos/application/publication/operation.py` stands at 491 of 500 effective
  lines and `hosted.py` at 55 (the product's own measure).
- An Attestation's predicate must hold a colon: the model's pattern refuses `release-rehearsal`
  and admits `release:rehearsal`. `record_attestation_once` returns the first member of a
  predicate and subject. The lifetime table holds no row for a rehearsal, so such a member
  would be open-predicate and end only by an explicit release.
- Of 12 tracked release bindings read beside the releasing checkout, 12 declare protected
  release tags, 12 hold a CI peer of the provider that hosts the rehearsal, and none declares
  the key.
- A synthetic observation of two CI peers whose runs passed serializes to 702 bytes at an
  indent of two, and to 812 with a rehearsal member of four fields; the result bound keeps an
  entry inline under 1,024 bytes.
- By the product's measure, `hosted_runs.py` is 130.9 line-equivalents and its tests 232.0;
  `hosted.py` is 60.1 and its tests, with the command's, 280.4; the release acceptance is 94.0
  and its tests 249.9. The catalog holds 47 commands, 9 groups and 111 operations.

DR-0026 asks that tag admission require the rehearsal's receipt. DR-0029 adds R14: a rule that
can block has a declared state, read through one function, and a release refuses only what an
earlier release reported; its law freeze admits no new rule from the tag of 0.2.0-beta.11 to
0.2.0 outside named exceptions.

## Goals / Non-Goals

Goals:

- The product can say, for one commit, whether a rehearsal exists and how it ended.
- The fact is stated where a release tag is read, one release before anything may refuse.
- A repository that does not opt in is read for nothing and refused nothing.
- The rule has a declared state from its first release.

Non-Goals:

- Any refusal. Every verdict, required gap and next action is what it was.
- A stored record, a command of its own and the offline check at `land --release`. Decision 6
  states their contract for the successor.
- Reading the rehearsal's receipt, which decision 9 of `release-rehearsal` builds when a reader
  needs it.
- The product-boundary check on the product's own binding (decision 8).
- A second provider. The reading is built for the provider that hosts the rehearsal.

## Decisions

1. **A head's rehearsal is its newest dispatched run that ran the verdict job, and that job's
   conclusion decides.**
   - **Rests on:** decision 8 of `release-rehearsal`: the verdict job runs for every rehearsal
     dispatch, succeeds only when every required leg passed, and is skipped in every other
     run; and the forge's listing of a commit's runs, which the hosted reader already uses.
   - **Considered:** the run's own conclusion, which cannot tell a rehearsal from a batch-head
     qualification of the same commit; and the receipt, which needs an artifact download, a
     second schema to validate, and a reading within the 14 days that the pipeline keeps an
     artifact.
   - **Chosen because:** a run at the head is bound to everything the head names: its tree, its
     version and its workflow file are the commit's own, so the plan's bindings hold once the
     listed row names the commit. The newest such run decides, whatever an older one said.
   - **Applies to:** the states `passed`, `failed`, `running`, `missing` and `unknown`. A
     dispatched run of the head that has not concluded makes the state `running`, since its
     jobs cannot yet tell whether it is a rehearsal. The predecessor set is not read from the
     run: the rehearsal's journey takes it from the record at the head, and the completeness of
     that record is the draft `release-predecessors-binding`'s. A re-run is read as the run's
     newest attempt, and the member names the attempt.
2. **The reader is the hosted reader's neighbor and shares its resolver and bounded listing.**
   - **Rests on:** `forge_web_repository` and `provider_rows`, which serve reviews and runs;
     the reader's table of provider words, which already maps a job's conclusion to a state.
   - **Considered:** widening `observe_hosted_runs`, whose rows and call count three callers
     and a size regression pin; and a client for the forge's REST interface, which needs a
     token reader.
   - **Chosen because:** one more listing with two more fields, the event and the creation
     time, and one read of a run's jobs for each dispatched run inspected, newest first, until
     one holds the verdict job. A full page, a row of another commit, an unknown word and a
     refused call are `unknown`, as they are for the hosted reader.
   - **Applies to:** a new module beside `hosted_runs.py`. The field names that the forge's
     CLI prints for a run's event, creation time and attempt are not confirmed against a
     forge; `hosted-observation` leaves the same confirmation to its lane (its task 5.2).
3. **The rehearsal is a member of the hosted observation, read at two of its three callers.**
   - **Rests on:** the three callers; the size of the publication operation module; and the
     measured entry of 812 bytes.
   - **Considered:** the command `ethos release rehearsal --head`, the plan's form, which adds
     two operations to a catalog of 111 and is the only caller of a reading that records
     nothing; and reading at the landing preview as well, which would state a missing rehearsal
     for every lane head.
   - **Chosen because:** the explicit observation is the command a release lane already runs
     for its head, and the probe of a release tag is where a release is read before it is
     published. The member holds the peer, the state, the run and its attempt, and the gap when
     the state is not `passed`. It is no entry of `observation_gaps`, so no verdict moves.
   - **Applies to:** `ethos publish --observe-hosted` and the probe of a release tag, where the
     binding opts in. The landing preview, the probe of the release branch and every apply
     read no rehearsal. The probe passes one argument, so the module near its bound gains
     about two lines.
4. **A repository opts in with `[release.rehearsal] peer`, and only then is anything read.**
   - **Rests on:** the plan's key; the paradigm's `release_binding_gaps`, which reports a key
     that no reader consults; the count of bindings in the Context.
   - **Considered:** reading every repository that declares a CI peer, which is a new rule for
     twelve bindings that have no rehearsal job; and a `job` key that names the verdict job,
     which adds a value to validate before any repository asks for another name.
   - **Chosen because:** the table has one key, and its value is the identity of a declared
     peer with the `ci_cd` capability. A table with another key, or a peer that the binding
     does not declare, is reported under `release-binding`, as an invalid record of
     predecessors is. No tree that passes today declares the table, since it is a required gap
     today, so no tree that passed its predecessor is refused.
   - **Applies to:** every governed repository. The verdict job's name is the product's
     constant, so a repository that opts in names its own verdict job `release rehearsal`. An
     engine older than this Change reports the table as an unread key, so the product's own
     binding declares it only in a lane whose selected runtime contains this Change.
5. **The rule is `release_rehearsal_unproven`, and it enters in the reporting state.**
   - **Rests on:** R14; the paradigm's `reporting` list and its one reader, `armed`, which the
     paradigm report and the commit hook already call; the release lead's condition of
     2026-11-17: this rule reports before it blocks and binds only a repository that opts in.
   - **Considered:** reporting as data without a declared state, as `hosted-observation` did,
     which leaves the arming Change to add the state and the refusal's code together; and a
     `state` key in the opt-in table, a second carrier of a rule's state.
   - **Chosen because:** the state is declared where rules declare it and read through the one
     function. The obligation name `release-rehearsal` joins the list. While it is listed, the
     gap `release_rehearsal_unproven:<state>` is part of the rehearsal member and of no required
     list. The code that would refuse is one branch behind `armed`, and it cannot run in this
     release.
   - **Applies to:** the probe of a release tag. The cost is a name in the list whose gap the
     paradigm report never raises, and a third reporting rule in the count of the law by
     state. The registry gives the code its meaning and its repair: dispatch the rehearsal for
     the head, then observe again.
6. **Nothing is recorded here, and the record's contract is stated for its first reader.**
   - **Rests on:** decision 5 of `hosted-observation`: a stored `running` still reads `running`
     after the run failed, and a record without a reader is unproved; the facts on Attestations
     and the measured neighbors in the Context.
   - **Considered:** the plan's record and command in this Change, estimated at 205 to 315
     product and 410 to 630 test line-equivalents more, for a reader, `land --release`, that
     this Change may not arm.
   - **Chosen because:** every reader of this Change reaches the forge, so a fresh reading is
     both smaller and more current than a record. A check at the tag's creation is offline and
     needs one. Its contract, for the Change that builds it: a command in the hidden `release`
     group reads as decision 1 reads and records, for a run that concluded, one member of the
     predicate `release:rehearsal` whose subject is the commit, whose verdict is the verdict
     job's, and whose body names the peer, the run, its attempt and creation time, and the
     head's tree, version and workflow blob as Git reads them. Members are added, not kept
     first: the member of the newest run decides. Its lifetime is the head's, as a proof's is.
     It mints no authority.
   - **Applies to:** the successor Change, owned by the release lead and read again at the cut
     of 0.2.0-beta.14. The plan's name `release-rehearsal` for the predicate cannot be issued;
     `release:rehearsal` is the name.
7. **Where the refusal sits, and in which release, are the owner's decisions.**
   - **Rests on:** DR-0026's words, DR-0029's law freeze, and the two places a release tag is
     read: its creation, offline, and its publication probe, which reaches the forge. Decision 2
     of `release-acceptance` armed a publish refusal for the product root alone, in the batch
     before this one, because the product's tree passed it.
   - **Considered:** arming at the tag's creation in this Change, which that condition and R14
     refuse; and arming at the probe in this Change, which is the same new refusal one step
     later.
   - **Chosen because:** this Change makes both later forms possible and decides neither. At
     the probe, the armed rule reads fresh and needs only the name's removal from the reporting
     list; a tag that the probe refuses already exists locally. At the tag's creation nothing
     exists yet, and the rule needs decision 6's record, a reading before each tag, and one
     more release that reports at that place before it refuses there.
   - **Applies to:** the owner's two decisions that the tasks name, read again at the cut of
     0.2.0-beta.14. The first release that carries the rule states the rehearsal at its own
     tag's probe and refuses nothing.
8. **The product-boundary check on the product's own binding waits for the arming Change.**
   - **Rests on:** the plan's last clause; decision 4's last sentence: the product's binding
     cannot declare the table in the landing that first reads it.
   - **Considered:** the check now, which fails the product's own proof until a later lane
     declares the table.
   - **Chosen because:** a check that the table is present guards a refusal against being
     switched off, and there is no refusal yet.
   - **Applies to:** the product repository alone. Owner: the release lead; read again with
     the arming Change.

## Risks / Trade-offs

- The reader is designed against the forge CLI's documented listing and no recorded answer.
  A key it misnames makes the state `unknown`; it cannot make a head pass. The first real
  reading is a lane task, after the first rehearsal of `release-rehearsal` has run.
- The sizes are estimates from the measured neighbors, with tests at twice their product; the
  hosted reader's tests are 1.8 times its module and the release acceptance's 2.7 times. That
  gives 100 to 155 product and 200 to 310 test line-equivalents for this Change, against a
  planned 200 and 170.
- The hosted observation counts every run of a commit alike: a failed rehearsal keeps its peer
  `failed` there after a second dispatch passed, until the failed run is run again. The
  rehearsal member reads the newest run, so the two can disagree for one head.
- A dispatched run of the head that is no rehearsal and has not concluded makes the state
  `running` until it ends.
- The verdict job's name joins the pipeline model and the product. A renamed job reads as
  `missing`, and a test of `release-rehearsal` pins the name.
- An opted-in repository's explicit observation of a head that is no release head states a
  missing rehearsal, as data.
- The member adds about 110 bytes to an observation entry. With more than two CI peers or a
  failed run the entry already leaves the inline bound, as `hosted-observation` records.
- Until a successor arms the rule, a release tag is created and published without a rehearsal
  exactly as today, and the release guide's step is the only requirement.
