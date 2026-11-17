# Design

## Context

At the base commit four places decide what a record is:

- `effective_record_roots` in `src/ethos/repository/profile.py`: the paradigm's immutable roots
  plus the profile's `record_roots`. Redaction reads it three times and the marker verifier once.
- `RECORD_PREFIXES` in `src/ethos/adapters/gates/native/inputs.py`: `evidence/`, `docs/archive/`
  and `openspec/changes/archive/`. The authored-input join and the staged text check read it.
- The same three prefixes as a literal in
  `src/ethos/repository/policy/quality/gate_composition.py`, which decides whether a repository
  holds authored documents at all.
- `IMMUTABLE_RECORD_ROOTS` in `src/ethos/repository/policy/quality/source_budget.py`: the archive
  alone, which the shipped format policy must repeat under `immutable_record_roots`.

The join has five call sites (`git grep -n "authored_source_files(" -- src` prints them and the
definition): the two format selections, the configuration gate, the link gates and the Markdown
file list that the Markdown and prose gates share. A profile's declared record root appears in
none of the last three places, so every file under it is judged in full, and the format apply
rewrites it.

The row's design note gave a direction in three points and asked three questions. Decision 1
takes the first point with one departure. Decision 3 answers the first question and departs from
the second point: a gate does not yet judge a record by its age. Decisions 6 and 7 answer the
other two questions.

## Goals / Non-Goals

Goals:

- One definition of the record set, read by every consumer that asks what a record is.
- A gate's verdict on a record file is the same in every plane.
- The format apply does not rewrite a declared record that the accepted branch already holds.
- No refusal is added to a proof, a commit or a push.
- A drift refusal names the way out for a path the repository does not author or does not want
  rewritten.

Non-Goals:

- Immutability for a declared root. The paradigm's `immutable_roots` stays the only such claim.
- Folding `docs/archive/` and `evidence/` into the record set; decision 1 gives the reason.
- A gate that reports older record content without refusing it. That needs a base that every
  plane resolves alike, which decision 3 leaves to the Change that binds a gate's base.
- A fetch, an environment variable or a second resolver for a trusted base.
- A list-spacing gate that follows a repository's formatter ignore file.
- The two rules that count one document's metadata twice. No record root decides either rule.

## Decisions

1. **One record set: the declared roots and the paradigm's immutable roots. The two other
   prefixes become the paradigm's retained roots, a second notion.**
   - **Rests on:** a reading of every consumer at the base. `_verify` in
     `src/ethos/application/redaction.py` refuses every difference under a root between its base
     and head that is not the redaction, and `_apply` blocks on an occurrence it cannot classify
     under a root. `record_marker_gaps` judges every hunk under a root. The existing case
     `test_python_role_partition_is_complete_and_non_overlapping[evidence/decision.py]` requires
     Python under `evidence/` to count as source.
   - **Considered:** folding the two prefixes into the set, as the design note proposed, which
     adds those three refusals for a repository that tracks either directory, where the law
     freeze admits none before 0.2.0, and lets code under `evidence/` leave the source budget;
     folding with a parameter that redaction, the verifier and the budget set, which keeps the
     same split under another name at five call sites; and listing them as immutable roots,
     which makes them redactable too and adds the claim that the third point of the direction
     forbids.
   - **Chosen because:** it adds no refusal and changes no redaction scope. The trade-off is that
     two notions remain: the record set, which redaction, the marker verifier, the source budget
     and the format repair read, and the retained roots, which no formatter, list rule or gate
     composition reads. The second is now declared once in the paradigm and is no longer a
     constant in three modules.
   - **Applies to:** the paradigm's `immutable_roots` and new `retained_roots`, joined once as
     `captured_roots`. A repository that wants `evidence/` redacted declares it, as before.
     Revisit when the structure rules design record roots after 0.2.0: that design decides
     whether the two notions become one.
2. **Each consumer keeps or narrows its cases.**
   - **Rests on:** the table below, read from the code at the base and after the patch; the
     regressions name each row that changes.
   - **Considered:** stating the rule without the cases, which is how a fix verified on one
     consumer reaches a second one unverified.
   - **Chosen because:** the gate for this row is that it adds no refusal.
   - **Applies to:** every reader of the two constants, of the literal copy and of the record set.
3. **A verdict judges every record file; only the repair reads a base (question 1).**
   - **Rests on:** three checkout shapes read through the product's one existing owner of a
     trusted base, the commit-range gate, run on the base's own code by a scratch script. With
     only a local accepted branch, with the accepted branch only as a tracking ref of `origin`
     under a detached head, and with no accepted-branch ref at all, the gate answers
     `commit_ranges_no_peer_remote` and resolves nothing; on a workstation with both declared
     peers fetched it resolves the accepted commit. The two hosted shapes are the fleet reader's
     observation of 2026-11-14, relayed by the release lead, with the second partly inferred.
     The same reader counted 2 of 13 readable governed trees that declare `record_roots`, one
     of 4 Markdown files and one of 26 files of four kinds; none holds code under a record root,
     and none has a record file that today's format gates refuse.
   - **Considered:** judging records by age in the gates against the merge base with the local
     accepted branch, under which a proof passes on a workstation and fails on the forge;
     reading the commit-range gate's tracking tips for the repair, which resolve on a
     workstation only and measured 71.0 product line-equivalents for the whole patch, over this
     row's limit of 60; and waiting for the base input before any change, which leaves the apply
     rewriting records.
   - **Chosen because:** a verdict must not move with something outside its subject, and a
     repair is no verdict. The cost is plain: until a proof binds a gate's base, a future format
     rule still refuses an older declared record in a gate. No governed tree is refused today.
   - **Applies to:** the source-format, Markdown, prose, link and configuration gates and
     `ethos lane format --check`, which judge every record file, and the preview and apply of
     `ethos lane format`, which keep older ones. The base as a named input of a proof belongs to
     the `gate-environment` draft.
4. **The repair's base is the merge base with the local accepted branch; a named path is
   repaired.**
   - **Rests on:** `prepared_work_lane`, the fixture of a Work Lane, where the accepted branch is
     a local ref of the lane's repository; and the regression that applies the format there.
   - **Considered:** keeping every record file unless it is named, which makes the apply useless
     for the record a lane just wrote; and keeping nothing, which is the behavior at the base.
   - **Chosen because:** the record a lane adds or edits is its own work, and the apply repairs
     it; what the accepted branch holds is not. Without a local accepted branch the apply keeps
     every file under a declared record root and names the base `unresolved`. The paradigm
     names the accepted branch, so the reader reads no binding for it. A base whose tree
     cannot be read is no base either: the reader then answers as it does without a base, so
     the read fails no caller, and the apply keeps every record.
   - **Applies to:** the preview and apply without paths. Naming a record asks for its repair.
5. **Kept records are reported by path.**
   - **Rests on:** no measurement of the alternative; its size was not built. The reports of
     `lane format`, the source-format gate and the Markdown format check already list `files`.
   - **Considered:** reporting nothing, which hides what the apply left alone and why.
   - **Chosen because:** `record_base` and `record_paths` tell the reader which base was read and
     which files the apply keeps, at the cost of two fields. In a gate they are information and
     decide nothing: the read that fills them cannot fail a gate or the format check, which
     the first form of this Change let it do through a base that could not be read.
   - **Applies to:** the three format reports. Both fields are empty when a request names its
     paths or the profile declares no record root.
6. **A declared root needs no migration (question 2).**
   - **Rests on:** the code and the fleet reader's count in decision 3. Nothing in this
     repository can count adopters: no governed-repository shape is known from here by number.
     At the base a declared root is judged in full, and it still is.
   - **Considered:** a profile key that turns the kept-record rule on, which adds a setting for
     a behavior that only protects bytes.
   - **Chosen because:** nothing a repository passes today is refused, so no repair ships with
     the release. The two trees that declare a root see one change: the apply stops rewriting
     what their accepted branch holds.
   - **Applies to:** every profile with `record_roots`.
7. **The rule lives beside the profile read the join already makes (question 3).**
   - **Rests on:** the source-budget measure of the patch against its base: the product total
     rises by 58.9 line-equivalents, of which the join's module adds 34.1, and the budget policy
     module loses 7.1 with its constant.
   - **Considered:** a new module for record selection, which adds a file for one function.
   - **Chosen because:** a repository without a declared root pays nothing: the function returns
     before it starts Git. One that declares a root pays three Git reads for each format report.
   - **Applies to:** `kept_record_files` in `src/ethos/adapters/gates/native/inputs.py`.
8. **The source budget reads the record set.**
   - **Rests on:** the direction's first point; the product's own profile, which declares no
     record root, so its budget does not move; and the fleet count that no governed tree holds
     code under a record root.
   - **Considered:** reading only the paradigm's immutable roots, which changes nothing and
     leaves the budget with its own notion of a record.
   - **Chosen because:** one set decides what a record is. The risk is relabeling: a profile can
     take a directory out of the budget by declaring it a record root. The declaration is a
     reviewed line of the profile, and neither `status` nor the paradigm report shows a
     profile's declared roots today; only the redaction preview lists them.
   - **Applies to:** `source_budget_report`.
9. **The policy key stays one release: expand, then contract.**
   - **Rests on:** a pristine checkout of the base that loads the shipped policy without the
     key through the base's own `policy_for_root`: it answers
     `source_budget_policy_invalid:shape`. This repository's commits and proofs are judged by a
     runtime built from the previous accepted head.
   - **Considered:** removing the key with the code that read it, which can lock the repository
     out of its own lane.
   - **Chosen because:** the new code accepts the key and ignores it, with a regression, so both
     builds admit the same file. The shipped policy is unchanged by this Change.
   - **Applies to:** `immutable_record_roots` in the format policy. Its removal is a follow-up
     for the release after this one.
10. **A drift refusal takes its next step from the gap registry.**
    - **Rests on:** the registry's `repair` field, the fixed next step of a code; the name rule's
      repair, which already names the two attributes; and `ethos lane format --check`, whose
      refusal carried no next action.
    - **Considered:** naming the attribute only for a path that is not authored, which the
      product cannot know before the repository marks it; and a second text in the lane command.
    - **Chosen because:** the registry is the one owner of a fixed repair. The text also names
      `record_paths`, since the check can refuse a record that the apply keeps.
    - **Applies to:** `ethos lane format --check`. A proof's source-format gate result names no
      next step yet; the `refusal-repairs` draft carries that.

The cases of decision 2:

| Consumer           | Case                               | Before       | After        |
| ------------------ | ---------------------------------- | ------------ | ------------ |
| Authored join      | Path under a captured root         | Not selected | Not selected |
| Authored join      | File under a declared root         | Judged       | Judged       |
| Format check       | File under a declared root         | Judged       | Judged       |
| Format apply       | Older file under a declared root   | Rewritten    | Kept         |
| Format apply       | New or changed file, declared root | Rewritten    | Rewritten    |
| Format apply       | Named file under a declared root   | Rewritten    | Rewritten    |
| Format apply       | Declared root, no local base       | Rewritten    | Kept         |
| Staged text check  | Staged path under a captured root  | Skipped      | Skipped      |
| Staged text check  | Staged path under a declared root  | Judged       | Judged       |
| Gate composition   | Path under a captured root         | Not authored | Not authored |
| Gate composition   | Path under a declared root         | Authored     | Authored     |
| Source budget      | Carrier under the archive          | Record       | Record       |
| Source budget      | Carrier under a retained root      | Source       | Source       |
| Source budget      | Carrier under a declared root      | Source       | Record       |
| Source budget      | Policy key absent or changed       | Invalid      | Valid        |
| Source budget      | Invalid profile                    | Measured     | Blocked      |
| Redaction, markers | Every case                         | Unchanged    | Unchanged    |

The blocked row reports `repository_profile_invalid` and is no refusal of a proof:
`compile_gate_declaration` in `src/ethos/repository/policy/gates.py` refuses an invalid profile
before any gate runs.

## Risks / Trade-offs

- Until a proof binds a gate's base, a future format rule refuses an older declared record in a
  gate, in every plane alike.
- The check can refuse a record that the apply keeps. Its next action names the repair: the path
  under `record_paths`, named in the request.
- A profile that declares a source directory as a record root takes it out of the source budget.
  The quality specification refuses relabeling source as generated content; no rule yet refuses
  relabeling it as a record, and no report shows the declared roots.
- The repair's base moves with the local accepted branch. It decides what the apply writes and
  no verdict.
- The policy keeps a key that nothing reads for one release.
- `record_paths` can be long in a repository with many records; it lists paths only.
