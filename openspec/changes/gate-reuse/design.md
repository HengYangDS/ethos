# Design

## Context

The product reuses no gate result. `run_gate_graph` accepts settled results
(`src/ethos/adapters/gates/runner.py:369-403`), and its callers pass only the readiness results of
the same run (`src/ethos/application/proof/operation.py:190`, `host.py:185`). An exact-source proof
binds its working content and index to the commit, untracked files that the repository does not
ignore included (`src/ethos/adapters/repo/worktree_postimage.py:64-86`), before and after its
gates. The policy digest binds each gate's execution identity and its `sources`; for a provider
that is the provider's own module file (`src/ethos/repository/policy/quality/sources.py:143-159`).
Quality evidence must name the proof's own tree
(`src/ethos/repository/policy/quality_reports.py:371-389`). The accepted requirement "Observation
reuse preserves freshness and result identity" already states the test of any reuse: clearing a
derived cache changes the cost of a computation and never its verdict.

The study of this Change, written on 2026-11-17 on the reviewed head of the batch of
0.2.0-beta.12, read the 34 gates of the full plan. An audit hook on file opens recorded what the
process of 28 gates read; the other six (`unit-architecture`, `local-install-smoke`, `build`,
`release-sbom`, `secrets` and `dependency-vulnerabilities`) were read by their code and not run.
The study and its spikes are not tracked. Its findings:

- 21 gates read a list of committed paths narrower than the tree, 2 read the whole tree
  (`secrets`, `source-budget`), and 11 read state that no tree digest holds: references and
  history, local Git configuration, ignored files, the prepared environment, the built artifact,
  the network or the clock.
- An equal tree is not enough. With the product's own source binding holding each time, an
  ignored cache directory at the root turned `generated-artifacts` from pass to block, a residue
  file that the local exclude file ignores made `repository-hygiene` fail, and an entry in the
  local attributes file removed one committed document from the files that every authored-text
  gate selects.
- `asset_classes` holds 19 names that no code maps to paths; its one consumer compares it between
  two declarations (`src/ethos/adapters/admission/control/replacement.py:149-155`). `ruff`
  declares `python-code`, and with only its configuration file changed its session went from pass
  to block.
- A first statement of inputs, written from the code for each of the 21 narrower gates, omitted
  at least one opened file for 11 of them. On a tree that differed in one unrelated document, 16
  gates kept their key and all 16 gave the same verdict; 5 of those 16 had an incomplete
  statement.
- The process of a provider does not see what its children read: the `openspec` provider opened
  none of the files under `openspec/`, which its Node child reads. 18 of the 28 traced gates
  start a child other than Git.
- In a hosted report of the suite (9,815 cases, 8,581.9 case-seconds), `tests/architecture` holds
  4.9% of the case time, the 55 unit modules whose text binds the repository root 7.3%, and the
  other 404 unit modules 87.8%. The textual sign is no boundary: recorded opens of 34 bounded
  runs showed one unit module without the sign reading `tools/` and the changelog, and one test
  module reading 69 files of `docs/`.

Outside sources, in the lead's reading of 2026-11-17, name the same failure. Bazel
(`bazel.build/remote/caching`) keys an action on its inputs, command line and listed environment
variables, does not track tools outside the workspace, and repairs a poisoned cache by deleting
it. Gradle (`docs.gradle.org/current/userguide/build_cache.html`) makes a task opt in, because
missing inputs "can cause incorrect cache hits". Turborepo
(`turborepo.dev/docs/crafting-your-repository/caching`) defaults to every source-controlled file
of a package. pytest-testmon (`testmon.org/blog/determining-affected-tests`) records what a test
executed and cannot see a data file that it read.

The owner decided the shape on 2026-11-17: the first release computes, records and compares, and
arming follows gate by gate where the record shows no mismatch.

## Goals / Non-Goals

Goals:

- Every gate of an executed exact-source proof run has an input key and a recorded verdict.
- A repeated key is compared with its earlier results, and a difference reaches the caller.
- The record shows, gate by gate, whether a later release may reuse a result, and which gates
  never may.

Non-Goals:

- Skipping a gate, in this release, by any route.
- A new declaration, refusal or required gap for a governed repository.
- Splitting `unit-architecture`; building a gate's child environment from a list; reuse on the
  hosted plane. Each has a named owner below.
- Changing the Attestation, the proof artifact, a policy digest or proof admission.

## Decisions

1. **The first release records and compares, and skips nothing.**
   - **Rests on:** the owner's decision of 2026-11-17; DR-0015, which lets no beta carry a defect
     that admits a wrong proof; the study's 11 incomplete statements of 21.
   - **Considered:** arming in the same release the gates whose statement looks complete, which
     saves at most 171.6 seconds of a documents-only proof (the 27 gates beside the seven
     largest) and rests on statements that no run has tested; and shipping nothing until review
     proves the statements, which gives no record from the governed repositories.
   - **Chosen because:** a wrong key costs nothing while every gate still runs, and only keys
     run on real trees show which are wrong. The trade-off: a proof gains under 0.4 seconds and
     saves none.
   - **Applies to:** every proof run of this release, local and hosted. No settled result comes
     from the record; a test pins the callers that pass settled results.
2. **The key is a digest over a stated list of committed paths and named inputs.**
   - **Rests on:** the study's comparison of five ways. One listing of the tree and 34 keys took
     0.1 seconds. Over the 211 documents-only commits since `v0.2.0-beta.10`, such a key stayed
     unchanged on 208 for the 13 gates whose statement holds no document, on 1 for the Markdown
     gates, and on none for a key over the whole tree.
   - **Considered:** the same key with the gate run on a tree of only its stated inputs: 23 of
     the 28 traced gates start Git, so that tree must be a repository, and a gate that enumerates
     files would silently check fewer. The key taken from what a run opened: a child's reads and
     absent paths are unseen. The whole tree alone: no hit on any of the 211 commits. A smaller
     proof floor for a documents-only difference: it saves most, changes proof admission, and is
     wrong where code reads a document.
   - **Chosen because:** it is the one way whose error can be observed before it is trusted: a
     statement can be compared with what the gate opened. The trade-off accepted is that a
     statement can be incomplete; decision 8 measures that.
   - **Applies to:** the gates of an exact-source run. The key holds each selected path with its
     mode and object ID, and the gate as its policy binds it: the whole row that the policy
     digest holds, with its execution identity and its bound sources.
3. **The product states what its own providers read, in one packaged table by provider ID.**
   - **Rests on:** `Gate` forbids unknown fields (`src/ethos/contracts/gates.py:138`), and an
     installed release admits a proof with its own compiler; the provider catalog already maps a
     stable ID to each provider (`src/ethos/contracts/gate-providers.toml`).
   - **Considered:** a new field of the gate declaration, which an older installed reader refuses
     and which changes every policy digest; reading `asset_classes` or `required_for_paths` as the
     statement, which the study showed to be incomplete for `ruff`; and a statement in each
     repository, which asks every governed repository to describe the product's own code.
   - **Chosen because:** the product owns its providers and is the only party that can keep the
     statement true to them. No repository declares anything and no digest changes.
   - **Applies to:** eight providers: configuration, the documentation registry, Markdown lint,
     module layout, OpenSpec, prose, schemas and the skill portfolio. The link check is not
     stated: on the product's own tree its process opened the committed target of a link, a file
     outside its traced statement, so it is keyed by the whole tree. The static code check was
     stated until the review of 2026-11-20 and is not: it judges Go modules and the scripts that
     a profile declares by path, and reads the repository's own linter configuration, none of
     which its statement selected, and a declared script is no pattern. Patterns have the form
     of `required_for_paths`. Every statement also holds the profile and the gate declarations.
4. **A gate without a statement is keyed by every committed path, and a provider that reads
   outside the tree is marked open.**
   - **Rests on:** the study's 11 gates that read outside the tree and the three results it
     changed on an equal tree; the product's 16 command gates, and the 32 command gates that the
     study of `gate-environment` counted in governed repositories, whose reads the product
     cannot state.
   - **Considered:** no key for such gates, which leaves a later reader unable to tell an unstated
     gate from an unrecorded one; and a guessed statement, which is the wrong hit.
   - **Chosen because:** a whole-tree key is true for a gate that reads only committed files, and
     the mark keeps a known open provider out of every later count.
   - **Applies to:** a command gate and a provider outside the table get the whole tree. The
     table marks as open the repository audit, the product audit and boundary, the
     generated-artifact check, the commit ranges, the type check and the Python behavior probe.
     A command gate carries no mark: five of the product's own read outside the tree, and
     decision 10 keeps every command gate from arming.
5. **Named inputs are the running product, the interpreter and platform, Git's version, Git's
   attribute classification of the committed paths and the names of the entries Git ignores.**
   - **Rests on:** the study's three results on an equal tree. Reading the classification of
     3,190 paths took 0.02 seconds, listing the ignored entries 0.05 seconds and Git's version
     0.007 seconds. Git is found on the launch path (`src/ethos/adapters/repo/git.py:86-100`).
   - **Considered:** a digest of the child environment, which would hash credentials that a child
     inherits; the versions of every installed tool, which the committed locks state for a locked
     tool; and a digest of the ignored files' bytes, which reads whole caches.
   - **Chosen because:** each named input was seen to change a selection or a verdict, and each
     is cheap to read. Where the running product was built from the proved tree itself, the
     committed files its wheel is built from are paths of every statement instead of a build
     identity; any other running build is named by its identity.
   - **Applies to:** every key. No value of an environment variable enters a key. Any other tool
     found on the launch path is not a named input; decision 10 keeps such gates from arming.
     The named inputs are read after the gates. The arming Change reads them before a gate, so
     a gate that creates an ignored entry misses once and is never a wrong hit.
6. **The record is one content-addressed file for each run, in the Git-common store.**
   - **Rests on:** the store's writer of content-addressed files and its record floor
     (`src/ethos/contracts/paradigm/paradigm.toml:198-216`); a record of 34 gates is 5,870 bytes
     on the spike, and reading 1,005 records took 0.07 to 0.14 seconds.
   - **Considered:** fields of the proof artifact, which the Attestation binds and every reader
     of a proof then carries; a member of the Attestation set, which gives a comparison the form
     of evidence; and a file in the worktree's ignored output, which a linked worktree and a
     later lane do not share.
   - **Chosen because:** the record is a derived cache: deleting it changes no verdict, and the
     worktrees of one repository share it. The record retirement owns it as one more kind under
     the existing record floor, 14 days by default.
   - **Applies to:** a run whose source still equals the commit after its gates: a governed
     proof, a host observation of an expected head, and a readiness run. Each row holds the
     gate, key, statement kind, verdict and duration; the record holds the head, the tree, the
     named inputs and a digest of the names, never the values, of the launch environment. A
     gate that an unmet prerequisite held did not execute and has no row. The result's data hold
     the record's name and the count of comparisons by state: a command's result is bounded at
     16 KiB (`src/ethos/result.py:29-30`), so the rows stay in the record. The record and the
     result's data also hold the count of effective lines, not blank and not a comment, of the
     Git directory's local attributes file, found through Git's own path for it: a count, never
     a pattern.
7. **A comparison is a note of the result, outside every check, and changes no verdict.**
   - **Rests on:** rule R14 of DR-0029: no release adds a required gap or a refusal to a tree
     that passed its predecessor; a result counts a diagnostic as adverse only at warning or
     error severity (`src/ethos/result.py:91-103`); a check's diagnostics enter the proof artifact
     (`src/ethos/adapters/mutation/proof_artifacts.py:95-125`).
   - **Considered:** a diagnostic of the gate's check, which would change the artifact's digest
     with the state of the record; a warning, which blocks; and silence outside the record,
     which hides a measured wrong hit from the session that produced it.
   - **Chosen because:** a mismatch is a fact about the key and not about the tree under proof,
     and a proof must be the same with or without a record.
   - **Applies to:** decided verdicts, pass and block, in both directions. An unknown result is
     recorded and not compared. The result counts the earlier results of another tree apart from
     those of the same tree, and names an open gate's comparison as open.
8. **The record names each committed file that a provider's process opened outside its
   statement.**
   - **Rests on:** two passes agree under any key, so the study's 16 agreeing verdicts held 5
     incomplete statements; DR-0029's rule that a table restating what the code holds is compared
     by a check; an audit hook added no time that two runs each of three gates could separate
     from their spread.
   - **Considered:** verdict comparison alone, under which a gate that always passes can never
     show a wrong key; and one test that traces every provider on the product's own tree, which
     sees one repository.
   - **Chosen because:** it turns the statement table from a claim into a measured fact on every
     governed tree. The trade-off: it sees the provider's own process and not a child.
   - **Applies to:** providers with a statement. Files of the running product and of the
     prepared environment are not counted. An open is attributed by the calling context, so an
     open on a thread that the provider starts itself is not seen. The hook is added once in a
     process, keeps nothing outside an executing stated provider and never raises; the record
     names a committed file by its repository path and nothing else.
9. **An Attestation asserts what it asserts today; a reused result will carry its own
   execution.**
   - **Rests on:** DR-0018, which reads a qualification as recorded; the artifact keeps a fixed
     set of fields for each check, so a reader that predates a field drops it; a proof's
     statement and claim are closed sets
     (`src/ethos/adapters/mutation/proof_validation.py:27-36`, `:171-183`).
   - **Considered:** the key in the proof artifact now, which changes every artifact digest for
     a field that no reader uses; and an armed proof that points at the record, which the record
     retirement may delete while a release tag still needs its proof.
   - **Chosen because:** in this release every check ran on the proof's own tree, so the
     Attestation's meaning is unchanged. At arming it asserts that each gate has a passing result
     whose input key equals the key of the proved head, and that each result names the tree it
     ran on.
   - **Applies to:** the arming Change: a reused check is copied whole into the proof's own
     artifact with its key and its execution's head and tree; admission computes the key of the
     proved head again and refuses a reused check whose key differs; a landing reads the proof
     as recorded. A gate with a quality axis cannot arm before a reader accepts the execution's
     tree in its evidence. At arming, a proof with a reused check carries a member of the proof
     statement, so the closed set of every earlier reader refuses it: `_statement_schema_gaps`
     in `src/ethos/adapters/mutation/proof_validation.py` answers `model_gap` unless the members
     equal the known names. A proof without a reused check keeps today's exact shape.
10. **A gate that starts a child other than Git does not arm before that child is built from a
    list.**
    - **Rests on:** the study of `gate-environment`: a declared command's child received all 156
      names of its launch, and a provider's child 16 of 20 markers; the product starts Git with
      an isolated configuration, a fixed locale and no inherited `GIT_` name
      (`src/ethos/adapters/repo/git.py:186-217`).
    - **Considered:** a key that holds the inherited environment, which decision 5 refuses; and
      trusting a spread of launches, which shows a difference only when a variable happens to
      differ.
    - **Chosen because:** an input that cannot be named cannot be keyed.
    - **Applies to:** the arming Change. It excludes the 16 command gates, which run as a child
      of the proof, and every provider with a tool child. Of the eight stated providers, four
      start no child or only Git and have no quality axis: `skills`, `docs-registry`, `schemas`
      and `module-layout`. They are the first candidates and hold almost none of a proof's time.
11. **A hosted run executes every gate.**
    - **Rests on:** a forge job starts from a clean runner with an empty store; the accepted
      scenario that a failed preparation cannot fall back on earlier proof artifacts
      (`openspec/specs/quality/spec.md:1098-1102`).
    - **Considered:** a key in the forge's cache, which any job of the project can write and
      which holds no custody.
    - **Chosen because:** the hosted run of a head is the independent execution that shows a
      wrong hit of a workstation. Its minutes stay as they are.
    - **Applies to:** every hosted job, in this release and after arming.
12. **`unit-architecture` is split in its own Change, by recorded reads.**
    - **Rests on:** the study's shares of the hosted report, and its finding that the directory
      and the textual sign both misplace modules.
    - **Considered:** a split by directory here, which the textual sign alone contradicts for
      7.3% of the case time; and by the selection of `fast-tier`, which names readers by text.
    - **Chosen because:** the split changes which paths the probe runs and how one coverage floor
      is decided for two parts, and the remainder of `fast-tier` changes the same probe.
    - **Applies to:** the remainder `test-gate-split`, read at the cut of 0.2.0-beta.14.
13. **A gate arms on its own record, at a threshold that the owner sets.**
    - **Rests on:** the owner's decision of 2026-11-17. With no failure in n independent
      comparisons the rate of wrong hits is bounded near 3/n at 95%: 10% for 30 and 1% for 300.
    - **Considered:** one count for all gates, which lets a gate that rarely changes ride on the
      comparisons of others; and a count of comparisons alone, which decision 8 shows to be weak.
    - **Chosen because:** a key is a claim about one gate. The recommended threshold for a gate:
      no mismatch and no file opened outside its statement, over at least 30 comparisons with a
      result of another tree, at least 10 distinct keys, 3 repositories and 3 launches, all
      inside the record floor.
    - **Applies to:** the arming Change. This release only produces the counts.
14. **The three accepted scenarios keep their text in this release.**
    - **Rests on:** nothing is reused here, so each stays true as written.
    - **Considered:** modifying them now, which would accept in the specification a reuse that
      no release performs.
    - **Chosen because:** an accepted scenario states what the product does.
    - **Applies to:** the later Changes, with this text. In "Change proof executes the complete
      test surface", `test-gate-split` replaces the second line with: "one decision of the
      attempt decides the coverage floor over the coverage of every part, and a part's evidence
      comes from an earlier execution only under an equal input key and then names that
      execution's tree". "Input changes during an audit" gains, at arming: "and no proof reuses
      a result of the dependency audit". "A required executable cannot be prepared" gains: "and
      a hosted run reuses no gate result of an earlier run".
15. **The 900-second requirement is amended when the first gate arms.**
    - **Rests on:** `unit-architecture` alone took 1,264.6 seconds, so no cold proof meets 900
      seconds. With every stated gate armed and the test gate split, a documents-only proof
      still owes `local-install-smoke`, the five other gates over 40 seconds and the tests that
      read the whole repository: an estimated 1,033 gate-seconds.
    - **Considered:** amending now, with no reused proof measured.
    - **Chosen because:** the requirement asks that cold and warm measurements be identified
      separately, and the warm one does not exist before arming.
    - **Applies to:** the requirement "Complete verification throughput preserves assurance".

## Risks / Trade-offs

- The time this row is meant to save is not in this slice and not in the first armed gates. It
  is behind the test split and behind `local-install-smoke`, whose artifact carries the commit's
  identity and so differs for every commit.
- A sound key does not make a pin bump cheap. A bump of the product changes the judge and so
  every key. In the repository that builds the product, the locks and the product's source are
  paths of every statement: 39 of the 53 commits that were not documents-only changed every key.
  A key by the version of each tool that a gate names is a later narrowing.
- A statement that is too wide only loses a hit. A statement that is too narrow is the wrong
  hit, and the record of opened files cannot see a child's read or a read of the environment:
  product code reads 19 environment names by literal. The arming Change lists the names that a
  candidate provider can reach. The review of 2026-11-20 found that unseen kind twice: the
  static code check's statement, and the configuration check's, which lacked the Vale
  vocabularies that its tool compiles. It also found two providers that read outside the
  committed tree and were not marked open, the external link check and the code behavior
  check. The table is corrected for the four. The statements of Markdown lint, prose and
  OpenSpec, the three other providers with a tool child, were not read against their tools
  again; decision 10 keeps every provider with a tool child out of arming.
- The record is local state. Deleting it loses comparisons and no verdict. A process that can
  write the store can write a record; that is the store's existing boundary, and it matters
  only from arming on.
- Reading earlier records costs time in proportion to their number, which the record floor
  bounds.
- An audit hook cannot be removed from a process, and readiness runs providers on several
  threads. An open with no gate in its calling context is not counted.
