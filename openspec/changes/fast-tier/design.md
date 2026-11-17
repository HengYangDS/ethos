# Design

## Context

See [proposal.md](proposal.md). At the base `ethos prove --readiness --execute` resolves the full
plan, runs the gates of its readiness tier and names the others as not run
(`readiness_observation` in `src/ethos/application/proof/host.py`). Resolving the plan of this
repository through `resolve_gate_policy` and `readiness_tier` gives 34 planned gates, 28 of them in
the tier. The tier's recorded time is 67 seconds beside 1,353 seconds for the test gate
(`openspec/changes/archive/2026-11-03-readiness-before-admission/proposal.md`).

The product selects no test. The behavior probe runs every test directory in a scratch that it
removes with the attempt, so no fact of one run reaches the next
(`src/ethos/adapters/gates/python_quality.py`). The product does hold the readers that a selection
needs: the code classifier that tells a test from a product file, the reader of a file's imports
that the deleted-input join uses, the step reader of the Forge pipeline files, and every planned
gate's command.

The product classifier reads 1,094 Python files in this repository at the base, 557 of them tests
(`observed_code_subjects` over `git ls-tree -r --name-only HEAD`). The two pipeline files hold 131
steps in 18 jobs (`ci_steps` over `forge_pipeline_files`). Their steps ask the task runner for 10
sessions and the planned gates' commands for 15; six sessions are asked for by a step alone.

Among the governed repositories of the workstation, 16 distinct profiles beside this one declare
their proof in three shapes (their tracked profile files): 7 name a gate registry, 8 declare gates
inline, and 7 declare a test gate inline, 5 as a command and 4 through a provider. The pipeline
template that the product ships runs one command, the full host proof
(`.config/ci/verification.cue`), so a repository on that template has no session that only a Forge
runs.

## Goals / Non-Goals

Goals:

- A readiness run names the tests that read what the lane changed, the changed paths that no test
  reads, and the sessions that only a Forge job asks for.
- A changed document or data file selects its readers, also when no test imports a changed module.
- The report costs seconds, adds no refusal and never changes a verdict.

Non-Goals:

- Running a test. The tier names the tests; the caller runs them with the native runner.
- A proof. A passing readiness run is not the full proof's pass and not the Forges' pass, and it
  writes no Attestation.
- A complete selection. A test that reads a file through a function and names neither the file nor
  its module is found by no rule on tracked text.
- Selection for languages other than Python, and a store of facts between runs.

## Decisions

1. **The tier reports the selection and runs no test.**
   - **Rests on:** the comparison of four ways in the study of this Change. A gate that runs the
     selected tests inside the readiness tier is a new blocking gate before admission, and a full
     proof would run those tests twice until the test gate is split. A mode that runs them under
     a host ticket was estimated at twice this Change's size and changes the command catalog.
     Selection from recorded facts needs a store that no run keeps today.
   - **Considered:** a readiness gate that runs the selection (a refusal that an existing
     invocation could meet; worse for the 900-second requirement); a new operation that selects
     and runs (about 300 product and 400 test line-equivalents, estimated); recorded facts (a new
     store root, and nothing learned before a first full run).
   - **Chosen because:** it is the one way that adds no refusal and leaves the 900-second
     requirement untouched, since a full proof never calls it. The trade-off accepted: the caller
     owns the test run and its host ticket.
   - **Applies to:** the readiness run. The plan's words "adds tests to readiness" stay open as a
     named remainder of the proposal.
2. **The report is one field of the existing readiness result.**
   - **Rests on:** the operation `proof.readiness`, whose result already names `not_run`; three
     test modules of this repository read that operation's name or handler, found with `grep`.
   - **Considered:** a read-only operation of its own, which gives the selection without running
     28 gates and costs a catalog row and the tests that pin the catalog's exact sets.
   - **Chosen because:** a new field breaks no reader, and the run's source is already bound to
     the committed head, which makes the committed difference the whole change.
   - **Applies to:** `data.unexamined` of that result. It repeats `not_run` as `gates`, so one
     field answers what was not examined.
3. **The selection is read from tracked text by five reasons.**
   - **Rests on:** a call of `readiness_unexamined` on this repository with a pretended base. Two
     changed paths select 5 tests, 18 select 66 (41 by import, 17 by name, 8 changed themselves)
     and leave 3 paths unread, and the 312 paths of a whole weekly batch select 498 of the 557
     tests. At the base one changed carried document selects 3 tests: 1 names it and 2 stage the
     package.
   - **Considered:** the full import closure, which the dense module graph turns into nearly
     every test; imports alone, which select no test for a document.
   - **Chosen because:** each reason can be checked by reading the test: it changed (`changed`),
     a changed `conftest.py` is in a directory above it (`conftest`), it imports the changed file
     or a file that imports it (`imports`), its text names the changed path (`names`), or it
     stages the package that carries the path (`stages`). A test keeps its strongest reason, in
     that order.
   - **Applies to:** Python files as the product classifier finds them, with the roles that the
     repository declares. The selection narrows a small change and not a batch.
4. **The package's carried files come from the wheel table of the Python manifest.**
   - **Rests on:** `pyproject.toml` of this repository, whose `force-include` table names 32
     sources (`carried_paths`), and the 2 test modules whose text names that table at the base
     (`grep -l`).
   - **Considered:** no such rule, which lists a carried document without a naming test as
     unread; a field of the profile that maps data paths to tests, which is a second list.
   - **Chosen because:** the table is the native declaration of what the package carries, and a
     test that names it stages the package from it.
   - **Applies to:** a manifest that declares hatch's wheel table. Any other manifest carries
     nothing for this rule, and a manifest that cannot be parsed makes the selection unavailable
     under its error, never empty.
5. **The sessions that only a Forge runs are read from the generated pipeline files.**
   - **Rests on:** `ci_steps`, the paradigm's own reader of both Forges' files, and the readiness
     gate `ci-projection`, which holds those files equal to the pipeline model in the same run.
     Read at the base: `external_links`, `host_conformance`, `hosted_verification`,
     `release_binary_scan`, `release_journey` and `suite_leg`.
   - **Considered:** evaluating the pipeline model, which needs its compiler and inputs in every
     repository; a list in the product or the registry, which was one session short within two
     days of its writing.
   - **Chosen because:** the files are what the Forges run, and one reader serves a repository
     with one Forge and no model.
   - **Applies to:** steps that ask Nox, the task runner behind the paradigm's Python runner
     entry, for sessions by name. A step that runs anything else is not judged, and the count of
     jobs read stands beside the list so that an empty list is not read as an unread pipeline.
6. **The base is the candidate branch, and only on a Work Lane.**
   - **Rests on:** the branch roles of the paradigm, and the binding of a readiness run's source
     to its head, under which the worktree holds no other change.
   - **Considered:** a base option, which is a new flag; the accepted branch for other roles,
     which selects a whole release's paths on an accepted root.
   - **Chosen because:** it is the base that the lane's proof and landing already use.
   - **Applies to:** a Work Lane. Any other role reports an empty base and no selection.
7. **A part that cannot be read is named and changes no verdict.**
   - **Rests on:** rule R14 of the committee's resolution: a rule that is new to governed
     repositories reports before it blocks.
   - **Considered:** a gap for an unreadable base, which an existing invocation in a checkout
     without a candidate branch would meet.
   - **Chosen because:** the report is advice about what to run next, and the gates alone decide
     a readiness run.
   - **Applies to:** the selection and the session list, each on its own under `unavailable`.
8. **No fact is stored between runs.**
   - **Rests on:** the open question of the archived `test-runner-unification` design, whether a
     probe keeps a per-lane cache, which that design gives to this Change.
   - **Considered:** a per-lane store of the paths that each case read, which finds the readers
     that name nothing.
   - **Chosen because:** every rule here reads the committed tree alone, so the report needs no
     owner of a store, no retention and no first run.
   - **Applies to:** this Change. The proposal names `test-tiers` as the reader of the question.

## Risks / Trade-offs

- [A reader takes the selection for the tests that suffice] → The reference and the field's name
  say what was not examined, `unread_paths` lists the changed paths without a reader, and the
  result keeps `not_run` and writes no Attestation.
- [The selection misses a reader] → One test module of this repository reads carried files
  through a product function and is selected by no rule here. The full proof and the Forges run
  every test; the tier claims no more than a lower bound.
- [The report takes time on a large repository] → Its cost is one read and one parse of each
  Python file: 0.4 seconds without a changed Python file and 2.7 to 3.7 seconds with one for this
  repository's 1,094 files, measured while the host's load stood near 29. The files are parsed
  only when a changed path is one of them.
- [The session pattern reads a command it does not understand] → It reads one line at a time and
  takes the names after Nox's session flag. A step that composes its command elsewhere is not
  read, and the count of jobs stands beside the list.
- [The import reader moved] → The deleted-input join and the selection now share
  `imported_modules`; the join's own tests keep its behavior.
- [The result's bound shortens the field] → A readiness result with 28 checks passes the bound of
  16 KiB. `apply_payload_budget`, called on a result of that shape with the report of 18 changed
  paths, keeps `base`, `changed_paths` and `forge_jobs` inline, names the field under
  `bound.partial` and writes the 66 tests and 6 sessions to the detail. A reader expands the
  result as for every large entry; the reference says so.
