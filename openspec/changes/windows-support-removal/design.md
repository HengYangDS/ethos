# Design

## Context

ETHOS built and tested for Windows without ever requiring it. Its two release legs were optional,
its suite leg was allowed to fail, and no adopter journey ran there. The cost was a second path in
the product wherever the host shows: access-control lists beside permission bits for a trust anchor
(the file that names the keys a repository trusts for commit signatures), a process listing through
the Windows management interface beside `ps`, a `cmd` launcher beside the shell one, zip archives
beside tar archives, a read path for hosts that cannot open a file through a chain of directory
descriptors, junction checks beside symlink checks, and a second set of kept environment names. Four
hosted legs, supply digests for two platforms and a host simulation in the tests followed from it.

The owner ended the support on 2026-11-25 for ETHOS and for every governed repository.

The fleet, read over the fifteen governed checkouts on the owner's host on 2026-11-25, and by the
archive URLs again on 2026-11-26: one repository tracks a retention record, and 2 of its 13 entries
name the platform `windows`; four repositories pin ETHOS's archives with rows for `windows-arm64`
and `windows-x64` (`architecture-publications`, `ddwg-essentials-film`, `ddwg-film`, `ethos-film`),
and none lists Windows in `lockfile_platforms`; five repositories' own CI files name Windows; seven
compile their pipeline declaration against the common CI model, and none of the seven names a
Windows runner. The census reads tracked text on one host; it reads no run and no repository
elsewhere.

Words used below. A governed repository **binds** a release when it moves its pin of ETHOS to that
release and runs `ethos hook install`, which selects the release's runtime and installs its hooks.
The **common CI model** is `.config/ci/verification.cue`, which ETHOS ships and against which a
governed repository's pipeline declaration is compiled. A **retention record**,
`.config/ci/retained-steps.toml`, names the CI steps that a repository keeps as shell programs. A
**self-landing** is ETHOS landing a change of itself, where the installed predecessor's hooks judge
the successor's tree. **This release** is the one that carries this Change: the release of
2026-12-05 if the lane lands by that cut, else that of 2026-12-12, both before 0.2.0 (the owner's
decision of 2026-11-26); **the next release** is the weekly release after it. A report that this
Change adds turns into a refusal only in a release after 0.2.0, as the freeze requires (DR-0029,
DR-0035).

## Goals / Non-Goals

**Goals:**

- One path in the product, the POSIX one, with no branch that selects a Windows form.
- Releases for `linux-x64`, `linux-arm64` and `macos-arm64`, each required.
- Accepted specifications, the contract, the guides and the tests state no Windows support and
  describe no behaviour that only a Windows host shows.
- Every governed tree that the copies run of DR-0029 reads at the tag passes under this release as
  it passed under 0.2.0-beta.12. Where a tree still holds a Windows declaration that this release
  would refuse, the tree is changed in its own repository before the tag; the release does not
  tolerate it. The two such effects are named in "What a passing tree meets" and put to the owner by
  name (task 1.3).

**Non-Goals:**

- Removing the detection of PowerShell and `cmd` scripts in a governed tree. It classifies files; it
  supports no platform.
- An arm macOS job in ETHOS's GitLab pipeline, and the rule for what each Forge runs (the owner's
  direction of 2026-11-25 that each Forge stands alone and their shared parts mirror each other).
  Both belong to a later Change on what each Forge runs; none is open yet. Until it lands, ETHOS's
  GitLab pipeline runs arm Linux alone.
- The governed repositories' own pipelines and pins.

## Decisions

- **The product keeps no branch that selects a Windows form.** Every `os.name`, `sys.platform` and
  platform-name parameter that selected one leaves with the code that only it reached, among it the
  `strict` mode of the process listing and the `cmd` console launcher. A function that took the
  platform's name as a parameter for tests (`process_commands`, `load_hook_contract`, the Node and
  native supply readers) loses the parameter. Branches between macOS and Linux stay.
  - _Rests on:_ the inventory; `rg -i 'windows|win32|os\.name' src/ethos` in the clone.
  - _Considered:_ keeping the branches unreached behind one constant. Rejected: the owner asked for
    no residue, and an unreached branch is tested by nothing.
- **Scenarios leave accepted requirements by a retiring edit.** The Change's first commit edits the
  accepted specifications directly: it deletes exactly the 27 scenarios listed below from 20
  requirements and changes nothing else (no line added, statements untouched, every requirement
  keeps at least one scenario). The delta specifications then carry only what is reworded or new.
  - _Rests on:_ OpenSpec 2.0.0 refuses a `MODIFIED` block that omits a scenario of the current
    specification and has no operation that removes one (its validator's message: "archive refuses
    to drop them"). The specification-governance resolution of 2026-11-16 names the retiring edit as
    the route "until OpenSpec ships an operation for it" (2.3, 2.5); the open Change
    `specification-governance` records that the owner confirmed on 2026-11-16 that ETHOS implements
    the resolution.
  - _How each clause of 2.5 is met here, since the product builds none of them yet:_
    - The list: the tables below, by requirement title and scenario name, each with its reason.
    - The comparison of base and head: no product reader exists. The author's script derives the
      retired pairs from the two trees; the lane's independent review runs it again on the commit
      and compares its output with the tables. The product's present signal for a removed step,
      `openspec_spec_obligation_removed`, does not see a step written as a list item, which is every
      step of these specifications: fed this edit's 82 removed step lines it names none. That defect
      enters the repository as a known-defect entry with this Change.
    - The owner's acceptance: the product's acceptance covers delta entries only, so the retired
      names and texts go to the owner in person, with the reworded and the added text, before the
      landing; the lane does not land without his answer.
    - The review question, "does the product still do this, or which title now states it?": the
      tables give the author's answer for each scenario. The independent review answers it again for
      each of the 33, and the section "Review of the retirements" below records the reviewer, the
      commit and each answer that differs, resolved before the archive.
    - A commit of its own: the first commit, which holds nothing else.
    - Open deltas: no open Change's delta names one of the 20 titles or a retired scenario (searched
      at `3c6260017`); the search is repeated at the lane's base and before the landing.
    - Arrival under 1.4: the edit refuses nothing.
  - _Considered:_ keeping each scenario's name and rewriting its body, as the Change
    `ci-emulation-retirement` did on 2026-11-02 (its design: "keeps its name"). Rejected: a scenario
    that is named for Windows and says that Windows is not supported is residue and retirement
    vocabulary (resolution 5.2). _Considered:_ `REMOVED` and `ADDED` under a new title for all 20
    requirements. Rejected: it changes 20 identities that keep their promise.
- **A requirement that would keep no scenario leaves by `REMOVED` and names its successor.** Three
  leave, with 6 scenarios. "Native metadata comparisons preserve observation semantics" (one
  scenario, on a Windows difference in change times) and "Runtime cleanup uses native host process
  authority" (three, on the management interface and PowerShell) each return as an `ADDED`
  requirement that states the same promise without a platform: "A read compares file metadata within
  one observation channel" and "Runtime cleanup observes consumers through the host's process
  lister". Their scenarios are verified by the existing tests of the merge observation and by two
  new tests of a failing and of a missing process lister. "Generated Windows verification jobs retry
  their source checkout" (two scenarios) leaves with the successor `none`. "Windows runtime archives
  fit the Windows path limit" is renamed to "A runtime archive names its runtime by a digest prefix"
  and keeps its one remaining scenario.
- **One requirement loses a step, not a scenario.** "Locked execution keeps native mise policy"
  keeps its scenarios; its scenario "An admitted command runs a host command" loses the step that
  described the Windows command baseline. No verdict changes.
- **The hook declaration and the launcher keep their bytes.** The shipped declaration keeps the
  entry `nt`, the launcher keeps the alternative of its path pattern that admits a drive-letter
  runtime path, and the reader takes the `posix` entry and accepts `nt` as the only other key.
  - _Rests on, run on 2026-11-25:_ an activation writes the launchers of the build that runs it and
    judges them against the declaration of the runtime that it selects. With the running build's
    launchers changed by exactly this alternative, the activation of a runtime that holds the
    present declaration ended with `hook_runtime_activation_invalid`, a `launcher_drift` gap for
    each of the four hooks and `hook_generation_digest`, and the selection went back to the earlier
    runtime. The product's one supported rollback, the current runtime activating the held one, is
    such an activation.
  - _Rests on, read and not run:_ the reader of every release through 0.2.0-beta.12 requires exactly
    the keys `posix` and `nt`, and a predecessor's reader meets a successor's declaration at a
    self-landing.
  - _So:_ the hook generation of this release equals that of `dev` today and of every release from
    0.2.0-alpha.19 to 0.2.0-beta.11 (one declaration, one digest, pinned by a test), and no
    activation between this release and one of them meets a difference in launchers or generation.
    0.2.0-beta.12 is tagged from `dev`.
  - _Considered:_ removing the alternative now. Rejected by the run above: the rollback from this
    release to its predecessor would be refused.
- **A retention record that names `windows` is read one release longer and reported.** The
  paradigm's platforms are `darwin` and `linux`; `windows` stands under `leaving_platforms`. An
  entry that names it stays complete, its step stays retained, and the audit reports
  `repository_paradigm_retained_step_platform` with its repair. The obligation
  `retained-step-platform` enters in the reporting state.
  - _Rests on:_ resolution 1.4, "Each new refusal reports for one release before it refuses", and
    R14 of DR-0029; the obligation `retained-step` is armed, so without this an entry naming
    `windows` would refuse a tree that passes today (one repository, two entries).
  - _Follows:_ the entry becomes incomplete no earlier than the next release, by the owner's
    decision recorded in the Change that arms it, which cites this release's reports.
- **Three gap codes leave with their only producers.**
  `git_object_trust_anchor_observation_unavailable` (raised only by the access-control reading),
  `hook_launcher_platform_invalid` (raised only for a platform without a declared entry) and
  `native_node_archive_members_invalid` (raised only for the zip archive of Node).
  - _Rests on:_ the registry is read from the package for a code's repair text; nothing in
    `src/ethos` or `tools` asks whether a code is registered (`rg '\bregistered\('` finds the
    definition alone), so no governed tree, stored receipt or entry is validated against it.
- **Protections that leave, each with its reach on a POSIX host.**
  - Junction checks (`is_junction` and `require_no_junctions`, with every call of them): a junction
    exists on Windows alone; every site keeps its symlink check.
  - Backslash and drive-letter checks in resource names and Git attribute names: on POSIX a
    backslash is an ordinary name character and no name is drive-anchored; the absolute-path and
    `..` checks stay.
  - The read path without descriptor chains: macOS and Linux always provide the chain, so the path
    was reached on no supported host. The reader still refuses a host without `O_NONBLOCK`.
  - Zip member checks of Node and native tools: ETHOS reads no zip archive any more; the tar member
    checks stay.
  - The access-control reading of a trust anchor: permission bits and ownership decide alone, as
    they did on POSIX. A refused permission change now carries
    `git_object_trust_anchor_protection_failed:<reason>`, which only the Windows path did before.
- **Release assembly takes one list of hosts.** `--hosts` replaces the required and optional lists;
  the record of legs left out and its sentence in the notes leave, as does the dispatch input that
  added the Windows legs to a push. A leg that carries another machine's runtime is refused with
  `release_assets_distribution_mismatch`, where the emulated leg was once admitted by declaration.
  Only ETHOS's own pipeline calls release assembly.
- **The locks resolve for macOS and Linux.** The Python lock declares its two environments; the
  constraint `uv<0.13.9` leaves with its reason, a Windows defect of that resolver; the Mise lock
  loses its Windows platform records.
- **The supply image is rebuilt inside the lane.** The Mise lock, the Python lock and the CI
  projection policy are inputs of ETHOS's supply image, so the projection check reports
  `supply_image_stale` until the image is rebuilt on the lane's GitHub proposal ref and its digest
  and source commit are bound in the pipeline declaration. The lane therefore publishes its proposal
  twice: once to build the image, and once after the commit that binds it.
- **Research records keep their dated observations.** Documents under `docs/research` state what was
  observed on a date about ETHOS and about other tools, Windows included; they claim no support. Two
  passages leave because they exist to steer Windows work in ETHOS: the section on native Windows
  security metadata and the items on Windows on Arm runners.
  - _Considered:_ removing every sentence that names Windows there. Rejected: it would rewrite what
    a dated record found about other tools.
- **Two known-defect entries name Windows.** The entry on a finished queue run that reports
  `host_admission_unavailable` is wholly a Windows defect and is closed; the release that first
  ships without Windows fills its `fixed_in`. The entry on a slot bound to its holder keeps its
  second reach, the place a proof takes for itself, and is reworded and renamed to that reach.
- **The contract's two sentences.** In `docs/governance/product-design-contract.md`: "Native macOS
  and Linux are required supported platforms; Windows support is desirable and claimed only after
  native qualification." becomes "Native macOS and Linux are the supported platforms."; and
  "Supported modern Python and native macOS/Linux/Windows behavior retain their declared floor."
  loses "/Windows".
- **The common CI model declares no Windows runner system.** A pipeline declaration that names the
  system `windows` no longer compiles against the model that this release ships.
  - _Rests on:_ the census: seven governed repositories name the common model in their tracked
    configuration, and none of them names Windows in a CI file. Within that reading, no tree that
    passes today is refused.
  - _Considered:_ keeping the system in the model for one release. Rejected: the model cannot
    report, only compile or not, and no declaration that the census read uses the value.

### What stays, and until when

A remainder leaves once the condition that ends it holds, and that condition is established before
the deletion; a kept piece has a stated end. Four pieces that exist only for Windows stay in this
release.

| Piece                                            | Why it stays                                                                                         | It leaves when                                                                                                                                                                               |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The launcher's drive-letter alternative          | A changed launcher makes the product refuse its own rollback across the change (run)                 | The activation writes the launchers of the runtime that it selects; that repair is a Change of its own, not yet open, and the alternative leaves in the release that ships it or a later one |
| The entry `nt` of the shipped declaration        | The reader of 0.2.0-beta.12 and of `dev` refuses a declaration without it (read)                     | No earlier than the next release, once ETHOS's own root and every governed repository that the releasing host can read select this release or a later one                                    |
| The reader's acceptance of `nt`                  | A later reader meets the declarations of releases through this one when it activates a held rollback | Once no governed repository that the releasing host can read selects, or holds as its rollback, a runtime whose declaration has the entry                                                    |
| `leaving_platforms = ["windows"]` and its report | A tree that passes today is not refused without a report                                             | No earlier than the next release, by the owner's decision in the Change that arms it                                                                                                         |

The reading for the second and third rows is each repository's `ethos/runtime/CURRENT` and
`ethos/runtime/ROLLBACK` under its Git common directory, read on the releasing host by the
maintainer of the governed repositories.

Not counted among them: the detection of PowerShell and `cmd` scripts, which classifies the files of
a governed tree, and the dated observations of the research records.

### Retired scenarios

Each leaves because it describes behaviour that only a Windows host shows, and ETHOS supports no
Windows host (the owner's decision of 2026-11-25). The last column answers the review question: does
the product still do this, or which title now states it? "No" means that the product has no such
path any more. A scenario name in that column is the reworded successor in the same requirement's
`MODIFIED` block, for a promise that holds on every host.

`command-plane`

| Requirement                                               | Retired scenario                                         | Still done, or stated by                  |
| --------------------------------------------------------- | -------------------------------------------------------- | ----------------------------------------- |
| Git signature trust observations are line-ending portable | Windows emits a valid CRLF signature status              | Git emits a valid CRLF signature status   |
| Git trust anchors use native host protection              | Windows anchor is ACL-protected                          | No                                        |
| Git trust anchors use native host protection              | Windows parent shell exports an incompatible module path | No                                        |
| Git trust anchors use native host protection              | Windows anchor is foreign-writable                       | An anchor is writable by another identity |
| Git trust anchors use native host protection              | Windows security facts are unavailable                   | No                                        |
| Git trust anchors use native host protection              | Windows protection operation fails                       | Protection cannot be established          |

`distribution`

| Requirement                                                          | Retired scenario                                 | Still done, or stated by |
| -------------------------------------------------------------------- | ------------------------------------------------ | ------------------------ |
| Content-addressed package publication is host portable               | Windows publishes an immutable package           | No                       |
| Native trust preflight preserves identity and failure meaning        | A foreign SID has no resolvable account name     | No                       |
| Platform support is established by native delivered behavior         | An emulating host qualifies an x64 runtime       | No                       |
| Platform support is established by native delivered behavior         | An emulated interpreter selects its runtime      | No                       |
| Hosted package construction uses runner supply and one Node resolver | Windows build resolves the installed Node layout | No                       |
| Release platforms catalog their archives on every hosted commit run  | A commit's Windows leg catalogs its archive      | No                       |
| One owner gives every journey child a fresh environment              | A Windows host runs a stage                      | No                       |
| Windows runtime archives fit the Windows path limit                  | A deep install root runs the interpreter         | No                       |
| Windows runtime archives fit the Windows path limit                  | The archive layout outgrows the budget           | No                       |

`proof-hosts`

| Requirement                                      | Retired scenario                                           | Still done, or stated by                                   |
| ------------------------------------------------ | ---------------------------------------------------------- | ---------------------------------------------------------- |
| Host conformance keeps local Git semantics exact | CRLF bytes are tested on a Windows-style Git configuration | CRLF bytes are tested under a converting Git configuration |

`quality`

| Requirement                                                         | Retired scenario                                                 | Still done, or stated by                                |
| ------------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------- |
| Interrupted commands retain effect and process ownership boundaries | Windows command timeout with a descendant holding its output     | A command times out while a descendant holds its output |
| Native tool supply has one declaration and bounded bootstrap        | Native Windows observation inherits another PowerShell's modules | No                                                      |
| The per-test bound detects hangs                                    | A Windows worker makes no progress                               | A worker makes no progress                              |
| Each Forge verifies a published commit once                         | A proposal leaves Windows on Arm to the landed commit            | No                                                      |
| Each Forge verifies a published commit once                         | A push leaves the Windows legs to a typed dispatch               | No                                                      |
| Hosted host conformance runs in declared tiers                      | The lane owner asks for the Windows legs                         | No                                                      |
| One aggregate check reports the per-push jobs                       | The Windows suite leg fails                                      | No                                                      |
| Suite legs repeat the test suite once for a release                 | The Windows leg fails                                            | No                                                      |
| Native adoption preserves declared byte identity                    | Native text mode would translate line endings                    | New bindings carry their declared bytes                 |

`repository-governance`

| Requirement                                            | Retired scenario                               | Still done, or stated by            |
| ------------------------------------------------------ | ---------------------------------------------- | ----------------------------------- |
| CI runner and retained-step records own their commands | A retained PowerShell step is owned as a whole | A retained step is owned as a whole |

`runtime-activation`

| Requirement                                       | Retired scenario                                 | Still done, or stated by |
| ------------------------------------------------- | ------------------------------------------------ | ------------------------ |
| Runtime image preserves native execution identity | A Windows standalone interpreter is materialized | No                       |

### Scenarios that leave with a removed requirement

| Removed requirement                                             | Scenario                                                            | Still done, or stated by                                             |
| --------------------------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Native metadata comparisons preserve observation semantics      | Stable Windows path and handle timestamps differ                    | A read compares file metadata within one observation channel         |
| Runtime cleanup uses native host process authority              | Package-only Windows PATH contains only Git                         | Runtime cleanup observes consumers through the host's process lister |
| Runtime cleanup uses native host process authority              | Native Windows PowerShell is unavailable                            | No                                                                   |
| Runtime cleanup uses native host process authority              | Native Windows process observation is unavailable                   | Runtime cleanup observes consumers through the host's process lister |
| Generated Windows verification jobs retry their source checkout | A Windows job starts while files of the previous job are still held | No                                                                   |
| Generated Windows verification jobs retry their source checkout | A runner declares another number of attempts                        | No                                                                   |

Two scenarios stay although they read close to this subject: a host whose locale is not UTF-8
("Process text is UTF-8 whatever the host locale") exists on POSIX, and a wheel reported through a
native file URL ("installed wheel uses a native file URL") is host-neutral.

## What a passing tree meets

The law this is read against, from DR-0029. R14: "Every rule that can block has a declared state,
read through one function. No release adds a required gap or a refusal to a tree that passed its
predecessor, unless an earlier release reported the rule and this release ships its repair." The
copies run: "Before each tag, the candidate is moved and proved on a disposable copy of every
governed tree the releasing host can read, in the selector form that tree holds. No tag while a copy
shows a new required gap or a new refusal in a tree that passed the predecessor, whatever the
source, outside R14's one exception: an earlier release reported the rule, and this release ships
its repair and names it in a Breaking entry. A session other than the batch's authors' reads the
result, and the entry prints the count for each gap code." The law freeze: "From beta.11's tag to
0.2.0, a narrowing or a ruled defect fix passes. A new rule, or a supply move that adds a gap, does
not. … The gate's pin rows are the named exceptions, each only in a release whose product ships its
repair." DR-0035 adds that a rule which enters in the reporting state and changes no verdict is not
a new rule of the freeze.

This release lies inside the freeze, and the removal of a platform is neither a narrowing nor a
ruled defect fix. Whether it lands there was the owner's to say; he decided it on 2026-11-26, and
DR-0038 (`docs/decisions/dr-0038-windows-support-removed.md`), the Change's decision record, carries
it with the four pieces that stay (his decision of the same day). What the Change does to a tree on
a supported host:

- **One new rule, reporting.** `retained-step-platform` enters in the reporting state and changes no
  verdict: a retention record that names `windows` is reported, not refused (one repository, two
  entries; task 2.3).
- **A value leaves the common model, with no report.** A pipeline declaration that names the runner
  system `windows` and is compiled against the common model does not compile; the model cannot
  report. No earlier release reported it. The census found no such declaration among the governed
  checkouts. If the copies run of the release finds one, DR-0029 allows no tag until the maintainer
  of the governed repositories changes that declaration in the repository's own lane; a tree that
  run cannot read meets the refusal at its bind.
- **The release supplies no Windows archive.** A Mise pin that lists `windows-arm64` or
  `windows-x64` for ETHOS's archive has no archive of this release to name there. Read on 2026-11-26
  from the tracked Mise files: eight repositories pin ETHOS by the `http:ethos` table and four of
  them list the two Windows rows (`architecture-publications` and the three film repositories). An
  upgrade by `ethos lane repair-paradigm --pin` replaces that table with the release's bare entry
  (accepted requirement "The paradigm repair declares the ETHOS selection on request"), so the rows
  leave with it. What a bind does with a hand-written table that keeps the rows is **not measured**,
  so it may be a second refusal that no earlier release reported; task 5.4 measures it in the lane,
  on copies of two of the four (`architecture-publications` and `ethos-film`), and records the
  result in "Measured". If a copy with the rows left in place shows a new gap or refusal, DR-0029
  allows no tag until the rows are gone from each of the four. The maintainer of the governed
  repositories removes them, each in that repository's own lane; the release Change's copies run,
  read by the release lead before the tag, shows whether they are gone. This order, rows before the
  tag, is the design's; the owner asked that Windows leave every governed repository and named no
  order.
- **No reach beyond ETHOS.** The three gap codes that leave and the hook declaration's key grammar
  reach no governed tree (Decisions), and the hook generation does not change. Release assembly's
  new refusal reaches ETHOS's own pipeline alone, which this Change changes with it. A refused
  permission change on a trust anchor keeps its exception type and gains the gap code in its
  message; a change that succeeds is untouched.

A tree on a Windows host has no release to bind. That is the decision itself.

## Measured

In a scratch clone, 2026-11-25 and 2026-11-26. The patch is the code, configuration and test part;
it holds no document.

- The patch, by `git diff --shortstat`, and the source budget, by the repository's budget report
  over the clone, are read on the final tree of the prototype and again at the lane's head (task
  5.2). Final tree: 189 files, 748 lines added, 3,714 removed. On `dev` `39a1a8ffc` it gives product
  84,342 lines (84,888 on `dev`), tests 112,928 (114,303), tools 8,631 (8,910); verdict pass, no
  gap.
- Tests, by `clone-check.zsh` over the whole clone (416 targets, one worker at two-minute cuts): 386
  targets ended, the guards 6 of 6 passed, lint and format clean, and 30 modules did not end inside
  the cut. Two failures, both expected and both in
  `tests/architecture/test_ci_provider_projections.py`: the supply image is rebuilt in the lane
  (task 5.1), and the other needs a `.venv`, which a clone has not.
- The 30 modules, under one host ticket (seven workers, the ticket's own cap; 16 minutes): 762 tests
  passed and 6 failed. The six are four cases of one release-recovery test and two of one
  merge-recovery test; each starts a child that imports the accepted checkout's installed ETHOS
  instead of the clone's source and is refused as a stale runtime build. All six fail the same way
  on the unpatched base in the same environment, so they are a limit of a scratch clone; the lane,
  which installs its own source, judges them.
- The shipped common model, rendered for every repository that uses it: the seven model
  repositories' declarations were compiled through this tree's own compile path and both Forge files
  compared with the files each repository tracks. Byte-identical in 7 of 7. An earlier form of the
  patch failed this in 7 of 7: it wrote `before_script` as a plain field, which moved that key in
  every generated GitLab job, so each repository's tracked file would have differed from the model's
  output and its projection check would have refused it. The model keeps the key in a comprehension,
  where it was.
- Rebased on 2026-11-27 in a scratch copy over the 12-05 stack (`dev` cdb51d469 with the cleanup
  patch and the Python-version patch, which land before this Change): tests 113,568, product 84,479,
  verdict pass; the shared test helper `tests/support/release_legs.py`, which the cleanup patch
  adds, holds the one host set after it.
- Specifications: the retiring edit removes 27 scenario headings and 82 step lines in 20
  requirements and adds no line; the Change then validates strictly; an archive in a copy leaves all
  twelve specifications valid.

## Rejected alternatives

- **Remove in the release of 2026-11-28.** The plan that the owner approved on 2026-11-25 ships that
  release as it stands.
- **Several Changes, one per area.** A product path, its tests, its requirement and its hosted leg
  leave together or the tree does not pass between them.
- **Refuse a retention record that names `windows` at once.** It would refuse a tree that passes
  today (R14).

## Risks / Trade-offs

- [A direct edit of accepted specifications is proven by no gate] → the tables list every retired
  scenario with its answer; the independent review reruns the comparison on the commit; the edit has
  a commit of its own; the owner accepts the retired text in person.
- [A POSIX branch was removed with a Windows one] → the test modules that import a changed module
  ran in the clone; the lane runs the whole pre-check, mutants for the protections that keep a POSIX
  reach, and the full proof before the landing.
- [An adopter binds before its Windows rows are removed] → task 5.4 measures a bind with the rows
  left in place; DR-0029's copies run is read before the tag; the maintainer of the governed
  repositories removes the rows, each in that repository's own lane.
- [A repository outside the census compiles a Windows runner against the common model] → DR-0029's
  copies run reads every governed tree that the releasing host can read, before the tag; a tree it
  cannot read meets the refusal at its bind, with the model's own message.

## Migration Plan

The lane is created after the tag of 2026-11-28, on a `dev` that holds the cleanup and the
Python-version patches of the 12-05 batch; its patch is rebased on them. Commit order: the retiring
edit; the product; delivery and CI; tests; the Change's documents; the supply image's binding after
the first push of the lane's proposal ref (the branch `proposal/<lane>` that a lane publishes for
review). Rollback before the landing is the lane's abandonment; after it, a revert Change, since no
state is migrated.

## Review of the retirements

(Written by task 1.4: the reviewer, the retiring commit, and each of the 33 answers that differs
from the tables above, with its resolution.)

## Open Questions

None for this Change.
