# Proposal

## Why

Nox sets the root logger to debug level and prints every record that reaches it. Repository
sessions such as `prose` and `markdown_lint` run their providers in the Nox process, and those
providers parse Markdown with markdown-it, which logs each block rule it tries at debug level, with
the parser state in the message. A six-line document produces 54 such records.

- On 11-03 one local `nox -s prose` run printed about 27 MB, nearly all of it markdown-it debug
  records, which buried the session's report.

## What Changes

- The repository's Nox sessions keep markdown-it's records below info level out of their output.
  The session reports and markdown-it's warnings and errors still print.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: Nox sessions do not print the debug records of the Markdown parser that runs inside
  them.

## Impact

`tools/ci/sessions.py`, the Nox toolchain architecture test and the changelog. The proof runs the
prose provider directly rather than through Nox, so hosted output does not change.
