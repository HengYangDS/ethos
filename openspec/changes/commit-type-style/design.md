# Design

## Context

See the [proposal](proposal.md). The type set is one list in the paradigm contract, and the
commit policy compiles its subject pattern from that list for every repository. The archived
Change of 2026-10-18 that brought the grammar gives its reason for ten types: "the grammar admits
the ten types that every declared policy shares".

## Goals / Non-Goals

Goals:

- A commit whose subject has the type `style` is admitted in every governed repository.

Non-Goals:

- Any other type. `spec` is in no published set.
- A command that rewrites a subject, and the repair of an unsigned commit in a lane's own range.
  The draft `refusal-repairs` holds the second.
- Naming the admitted types in the refusal of a subject. The same draft holds refusals that say
  less than their reader needs.

## Decisions

1. **The set is the conventional configuration's eleven.**
   - **Rests on:** the owner's decision of 2026-11-19; Conventional Commits 1.0.0, which names
     `@commitlint/config-conventional` for the types beside `feat` and `fix`; that
     configuration's list, read on 2026-11-19: build, chore, ci, docs, feat, fix, perf, refactor,
     revert, style and test.
   - **Considered:** keeping ten and leaving the rewrite to each repository; admitting every type
     that a former policy held, `spec` among them.
   - **Chosen because:** ten was the common part of five policies of one day and no judgement of
     `style`. A set that equals a published one needs no list of exceptions, and a commit written
     by its convention is not refused.
   - **Applies to:** every governed repository from the release that carries this Change. A
     repository's own `subject_pattern` stays a restated grammar, whatever it admits.
2. **Nothing migrates.**
   - **Rests on:** the grammar is read when a commit is admitted and when a range is judged; no
     record stores a commit's verdict.
   - **Considered:** a note for repositories whose former subjects used `style`; teaching the
     paradigm repair to remove a `subject_pattern` that restates the former ten types.
   - **Chosen because:** a subject that was refused for the type alone is accepted once the
     release is bound, and every accepted subject stays accepted. A second known grammar in the
     repair would keep the former reading beside the present one. Of the fourteen governed
     checkouts on the releasing host, read on 2026-11-19, one declares a `subject_pattern`: its
     own, which already admits `style`. The three repositories with no checkout there were not
     read.
   - **Applies to:** commits already made, in accepted history and in lanes.

## Risks / Trade-offs

- A type that is admitted cannot leave again without refusing the commits that used it. The set
  is therefore tied to a published one and not to a repository's request.
- A workspace that restates the former ten-type grammar keeps refusing `style`, and the
  paradigm repair no longer removes that field, because it removes only a pattern equal to the
  present grammar. The gap is still reported with its repair, the removal of the field.
- `style` and `refactor` overlap for a change of form. The grammar judges the subject's syntax
  and not the choice between two admitted types.
