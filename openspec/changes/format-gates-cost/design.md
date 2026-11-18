# Design

## Context

The gates' own records gave the lead: `source-format` was the slowest check in seven of eleven
governed trees in the copies run of 0.2.0-beta.11. A profile of each gate on ETHOS's tree and
on one governed checkout showed where the time went: in starting processes, not in formatting.

## Goals / Non-Goals

Goals:

- The number of native runs of the three gates does not grow with the number of clean files.
- No verdict, postimage or configuration rule changes.

Non-Goals:

- Sharing one result among the three gates of one proof. They still each check the files they
  own; the draft `gate-reuse` carries that.
- The suite and the install smoke, which are ETHOS's own proof time.

## Decisions

1. **The repository is listed once for each report.**
   - **Rests on:** the profile: 336 and 485 Git processes in the two gates for one fact each.
   - **Considered:** a cache inside the lookup, keyed by the root. A cache outlives the report
     that filled it, and a later call would read a tree that has changed.
   - **Chosen because:** an argument passed down has the report's lifetime and no other.
   - **Applies to:** `native_repository_configuration`, `native_configurations` and their
     callers in the format gate.
2. **The ignore file is read by Prettier's own interface, in one process.**
   - **Rests on:** Prettier's command line answers the question for one file at a time, and its
     programming interface answers it for any file with the same ignore file.
   - **Considered:** passing the ignore file to the bulk check. A file it excludes is then not
     listed as drifting, and the gate could not tell it from a clean file, which gets the list
     rule applied where an excluded file is left alone.
   - **Chosen because:** the answer comes from the tool that owns the rule, and an excluded
     file keeps exactly the treatment it had: its bytes are its postimage.
   - **Applies to:** `prettier-ignored.mjs` and `_repository_ignored`.
3. **`markdown-lint` takes its format verdict from the format gate's bulk path.**
   - **Rests on:** both gates select the same Markdown files by the same ownership.
   - **Considered:** dropping the format part of `markdown-lint`. Its dimension
     `markdown-format` is declared, and a repository may run the gate alone.
   - **Chosen because:** one path prepares a postimage, so the two gates cannot disagree.
   - **Applies to:** `markdown_lint_report` and the new `source_postimages`.
4. **The native check runs are a module of their own.**
   - **Rests on:** the per-file ceiling of 500 effective lines, which the format module passed
     at 532 with the first three decisions, and the commit hook's refusal of it.
   - **Considered:** raising nothing and trimming lines. The module then stays at its ceiling
     and the next change meets the same refusal.
   - **Chosen because:** the format module holds two things: one file's postimage, which several
     callers use, and the question which files a native check vouches for. The second has two
     entry points and no caller outside the gate, so it is the seam.
   - **Applies to:** `format_checks.py` (168 effective lines) and the format module (383).

## Risks / Trade-offs

- The new script runs under the product's Node with Prettier's module from the product's own
  supply. A Prettier release that changes that interface fails the gate loudly: the script's
  output is parsed, and diagnostics refuse.
- A file under a directory that Prettier's check skips still renders alone, as before.
- The figures were taken on a loaded host; the counts of commands are exact and are what the
  tests hold.
