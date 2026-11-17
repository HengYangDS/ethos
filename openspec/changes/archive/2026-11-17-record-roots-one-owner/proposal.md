# Proposal

## Why

The archived `rc-scope-plan` design names this row in its batch of 2026-11-28, and the committee's
resolution that DR-0029 records keeps it there. Decision 1 of the archived `common-base-plan`
design states the rule it serves: record roots and archived Changes report older content only.

ETHOS defines a record three times, so a governed repository cannot declare a record that its
format repair leaves alone. The paradigm's immutable roots with the profile's declared record
roots serve redaction and record markers; a fixed list of prefixes serves gate input selection
and the staged text check; a third constant serves the source budget. Gate composition repeats
the fixed list a fourth time. Reported by the adoption session on 2026-11-13 and measured since:

- One repository's declared decision records are an input of the Markdown, list-spacing and
  source-format gates. Another's own formatter ignore treats its plans as immutable, yet ETHOS
  formats them.
- The list-spacing gate runs over every authored Markdown file, while `lane format --apply` skips
  what the repository's formatter ignore lists, so a release entry's stated repair is a no-op for
  the files that fail.
- A format refusal on a received file names no way out: `source_format_drift:<path>` for two
  upstream licenses, with no next step that names the Git attribute.
- The same documents are counted by two rules: 186 rows of missing metadata and 90 paradigm rows
  for front matter in one repository.

## What Changes

- One record set, the effective record roots of the profile, is read by the source budget,
  redaction, the marker verifier and the format repair. The two constants and the fourth copy go.
- The two fixed prefixes that are no record root, `docs/archive/` and `evidence/`, become the
  paradigm's retained roots. With the immutable roots they are the roots that no formatter, list
  rule or gate composition reads, as before; the staged text check reads them from the paradigm.
- A verdict judges every file under a declared record root, in every plane: the format gates and
  `ethos lane format --check` behave as before. The repair is no verdict: the preview and the
  apply of `ethos lane format` leave alone a declared record file that the merge base with the
  local accepted branch holds unchanged, and every such file when that base does not resolve. A
  named record is repaired. The format reports name the base as `record_base` and the kept files
  as `record_paths`.
- Immutability stays a separate, explicit claim of the paradigm. No record root becomes immutable.
- The source budget counts a carrier under a declared record root as a record. The format policy's
  `immutable_record_roots` key is no longer read; the shipped policy keeps it for this release.
- A `source_format_drift` refusal of `ethos lane format --check` names its next step: the apply,
  the naming of a kept record, or the Git attribute that marks a third-party or generated path
  received.
- The drafts `refusal-repairs` and `gate-environment` gain this Change's follow-ups.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: ADDED `Record roots have one definition`, `The format repair keeps
older declared records` and `A format drift refusal names its ways out`.

## Impact

`src/ethos/adapters/gates/native/inputs.py`, `formatting.py` and `tool.py`,
`src/ethos/adapters/mutation/source_format.py`, `src/ethos/adapters/repo/hook/staged_text.py`,
`src/ethos/repository/policy/quality/gate_composition.py` and `source_budget.py`,
`src/ethos/domain/source_budget/measurement.py`, the paradigm declaration and its model, the gap
registry, their tests, `docs/reference/configuration.md`, `docs/reference/operational-roots.md`,
`CHANGELOG.md` and two draft proposals.

This adds no refusal in a proof, a commit or a push; the design lists each consumer's cases
before and after. It does not make a gate report older record content without refusing it: that
needs a base that every plane resolves alike, which the `gate-environment` draft carries. It does
not fold the two retained roots into the record set, and it does not repair the two rules that
count one document twice, which no record root decides.
