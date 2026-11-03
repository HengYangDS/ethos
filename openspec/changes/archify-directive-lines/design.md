# Design

## Context

See [proposal.md](proposal.md). The prose gate runs Codespell, then the Vale policy that ships with
ETHOS, then a repository's own `.config/checks/vale/vale.ini`, each on copies of the authored
inputs, and a finding of either Vale run blocks the gate. Vale applies every format section whose
glob matches a file, so `guide.archify.md` matches both `[*.md]` and `[*.archify.md]`. In an Archify
draft a line that starts with `@` and a directive name, such as `@answer`, `@meta`, `@source` or
`@sequence`, is a directive with `key=value` arguments.

## Goals / Non-Goals

**Goals:**

- Archify directive lines are not read as prose in any governed repository.
- The prose of an Archify draft keeps every rule of the Markdown policy.

**Non-Goals:**

- A repository-declared exclusion, which would let a repository relax the shared floor.
- The pipe rows that follow some directives; a draft keeps paths and commands out of them or in
  JSON diagram files.
- Markdown lint, which the drafts satisfy once no directive carries a bare URL.

## Decisions

- **Vale's native `BlockIgnores`, scoped by file name.** `[*.archify.md]` sets
  `BlockIgnores = (?m)^@[a-z][a-z-]*\b.*$`, so only a line that starts with `@` and a directive
  name is ignored, and only in an Archify draft.
- **Whole lines, not single arguments.** Paths, URLs and identifiers appear in many arguments of
  many directives; ignoring the line keeps the policy to one pattern.

## Risks / Trade-offs

- [A title or scope in a directive argument is no longer checked] → Such labels are short, and the
  draft's headings and paragraphs, which carry its prose, keep every rule.
