# Proposal

## Why

ETHOS defines a record three times, so a governed repository cannot declare a record that its
format gates leave alone. The paradigm's immutable roots with the profile's declared record roots
serve redaction and record markers; a fixed list of prefixes serves gate input selection and the
staged text check; a third constant serves the source budget. Reported by the adoption session on
2026-11-13 and measured since:

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

- One record set, the effective record roots of the profile with the paradigm's defaults, read by
  gate input selection, the staged text check, the source budget and redaction. The two constants
  go.
- Records are judged by age: content that the trusted base tree already holds is reported only,
  and a new or changed record file is judged.
- Immutability stays a separate, explicit claim.
- A format refusal on a path outside the authored set names the attribute that excludes it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

Gate input selection, the staged text check, the source budget and their tests. Open: whether the
report of older content needs the base tree of the common-base plan first, and which repositories
rely on format gates over their record roots.

Owner: the release lead. Next action: answer the design note's three questions and measure the
patch. Read again: at the cut of 0.2.0-beta.12.
