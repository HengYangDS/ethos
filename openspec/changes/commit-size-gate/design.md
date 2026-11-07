# Design

## Context

`code_size_gaps` in `src/ethos/repository/paradigm/size.py` reads `root / path` for every authored
file of a registered language and compares its effective lines, lexed or Python-measured, with the
`size.code_effective_lines` parameter; its only caller is the paradigm report. `_pre_commit` in
`src/ethos/adapters/repo/hook/admission.py` scans staged secrets, checks staged Python format on
index blobs and runs the staged prewrite.

## Goals / Non-Goals

Goals:

- One measure for the report and the hook, judged on the bytes each one admits.

Non-Goals:

- The docs registry's document ceiling, which needs its generated-output and origin rules at commit
  time.

## Decisions

1. **One measure.** `effective_lines(language, source)` in `size.py` returns a source text's
   effective lines under its language's measure; `code_size_gaps` applies it to worktree files and
   the hook to index blobs.
2. **The hook reads index blobs.** A `staged_size` module of the hook package lists the staged
   regular files with `git diff --cached --raw`, since a symlink or gitlink holds no source, drops
   the received paths as the report does, reads each blob with `git show :<path>` under the hook's
   index environment and takes the ceiling from the invocation's bound parameters. It raises
   `pre_commit_code_size_exceeded:<path>:<lines>><ceiling>`, or
   `pre_commit_code_size_unmeasurable:<path>` for a blob that is unreadable or not UTF-8.
3. **Its own module.** `admission.py` holds 453 of its 500 effective lines, so the check is a module
   that `_pre_commit` imports on demand, as it imports the prewrite.

## Risks / Trade-offs

- The hook resolves the ceiling from the worktree's rules binding, as readiness does; a commit that
  changes the binding and a file together is judged against the worktree's value.
