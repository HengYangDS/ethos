# Proposal

## Why

The known defects of ETHOS are written only into each release's changelog entry, as a list that is
copied from release to release by hand. A defect has no file of its own, so no lane can record it
with the work that found it, close it with the work that repairs it, or have its text reviewed. The
owner decided on 2026-11-19 (「按照 A」) that the known-defect record is a carrier inside the
repository, complete and usable with no remote, and that the two Forges' tickets are at most
projections of it.

This Change is the first step of that carrier: the entries enter the repository as tracked text.
The command that reads them and the check that reports a malformed entry are later Changes.

## What Changes

- A root directory `defects/` holds one Markdown file per known defect, named by the defect's
  subject. Each file has five TOML fields between two `+++` lines (`title`, `state`, `since`,
  `fixed_in`, `workaround`) and prose. The form and its reading rules are in this Change's design.
- 73 entries enter: 65 open and 8 closed. The closed ones are repaired on `dev` and wait for the
  release that carries the repair to fill their `fixed_in`.
- The markdownlint configuration gains `defects/**/*.md` in its `globs`, so that a direct run of the
  tool reads the files that the product's `markdown-lint` gate already reads.
- The shipped Vale policy ignores the front-matter field `workaround`, as it already ignores seven
  front-matter fields of other documents: Vale lints a TOML field as plain text, where a code span
  is no longer code and the term rule refuses the lowercase product name inside a command. An
  entry's `title` stays linted, as every document's title is. This file is the common policy that
  every governed repository's `prose` gate runs first, so the change reaches every governed
  repository; it only removes diagnostics, of every Vale rule (terms, repetition and the
  plain-language rules) and in that one field only.

No product code, no requirement and no accepted requirement changes. Two shipped configuration
files change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No specification states the entries yet; the read command that will is a later Change, so
`skip_specs: true` applies.

## Impact

- The repository root gains one directory of records. A non-dot root directory needs no
  declaration, and the product's Markdown gates already take every authored `*.md` file at any
  depth.
- A governed repository gains no directory and no gap. Its `prose` gate stops reporting Vale's
  findings inside a front-matter field named `workaround`, in YAML or TOML front matter; the
  spelling check still reads that field. Its `markdown-lint` gate is unchanged: the gate names its
  files itself and does not read the configuration's `globs`.
