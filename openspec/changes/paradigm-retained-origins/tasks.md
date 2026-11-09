# Tasks

## 1. Behaviour

- [ ] 1.1 Exclude verified originals from the authored checks. Done when paradigm tests show a byte-
      and mode-verified original, including one named like a decision record and one in a
      non-kebab directory, with no front-matter, decision-record, authored-name or formatter gap,
      and an altered, mode-mismatched or merely declared original, a malformed taxonomy and an
      ordinary document without front matter keeping theirs; the formatter case uses a fixture
      whose only Markdown file is the original.
- [ ] 1.2 Repair no original. Done when a `repair_paradigm` test with a `<!--`-wrapped verified
      original plans no edit of it, and the same file without verification keeps its planned edit.

## 2. Acceptance

- [ ] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there.
