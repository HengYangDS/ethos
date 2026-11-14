# Design

## Context

See the [proposal](proposal.md). `authored_source_files` has five call sites: the format selection
(`prepare_source_format` and `source_format_report`), the configuration gate's candidate selection,
the link gates and the Markdown file list that the Markdown and prose gates share. `received_paths`
in `src/ethos/adapters/repo/git_attributes.py` reads the two attributes through `git check-attr`;
`paradigm_received_paths` adds the repository's verified byte-bound carriers.

## Goals / Non-Goals

Goals:

- No check that reads authored input selects a path that Git attributes mark received.
- One place subtracts those paths for every caller of the join.

Non-Goals:

- Any change to byte-bound carriers. Format selection already leaves them alone through their
  `forbidden` mutation policy, and the Markdown, prose and configuration checks read them on
  purpose.
- A new gap code or a new attribute.

## Decisions

1. The subtraction lives in `authored_source_files`. Each of its callers reports findings that only
   an edit of the file repairs: format drift, list spacing, Markdown lint, spelling, links and parse
   errors. For a received file that edit rewrites a third party's or a generator's bytes, so no
   caller needs to see it. `pre-commit` already leaves these paths alone, and it exists to refuse
   the bytes that the gates would refuse.
2. The join subtracts `received_paths`, not `paradigm_received_paths`. A byte-bound carrier is the
   repository's own content under custody; its read-only checks stay, and its format exclusion
   already comes from format ownership.
3. A named received path is refused by the existing rule for a requested path outside the join:
   `source_format_other_owner:<path>` from `lane format`, and the configuration gate's target with
   another owner. Both state the fact, so no gap code is added.
4. `authored_text_files` drops its own `received_paths` subtraction. Its only callers pass the
   join's output, so the second read of Git attributes selected nothing.

## Risks / Trade-offs

- Marking a path vendored or generated now also removes it from the Markdown, prose, link and
  configuration gates. The same marking already removes it from the name rule, the code ceiling and
  the hook's text check, and it stays visible in `.gitattributes`.
- The join runs one more `git check-attr` per call. When Git cannot be started it raises, as the
  join's inventory read does; when Git answers with an error, nothing is received and every path
  stays judged.
