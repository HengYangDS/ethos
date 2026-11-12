# Proposal

## Why

On 2026-11-12 the owner asked for clear, enforced blank-line rules in every document format. The
native formatters already decide them for Markdown, YAML, JSON and JavaScript (Prettier), TOML
(Taplo with `allowed_blank_lines = 1`), Python (Ruff) and CUE (`cue fmt`); each collapses runs,
strips leading and trailing blank lines and ends the file with one newline, as measured on
2026-11-12. The files that the format policy gives to `repository-canonical-text` have no owner
that acts: INI and `.cfg` files, the Vale vocabularies, `LICENSE`, `VERSION`, `.editorconfig`,
`.gitattributes`, `.gitignore`, `.gitkeep` and `.shellcheckrc`. Their declared format command,
`nox -s format -- hygiene`, names a session that does not exist, `ethos lane format` skips them,
and only ETHOS's own hygiene audit checks their final newline; a governed repository checks
nothing.

## What Changes

- `repository-canonical-text` becomes a real formatter: no blank line at the start or end, at most
  one blank line in a row, whitespace-only lines emptied, and one final newline; an empty file stays
  empty, and content lines keep their bytes.
- `ethos lane format --check` and `--apply`, the source-format gate and `pre-commit` apply it, in
  ETHOS and every governed repository.
- The format policy's four canonical-text rows name `ethos lane format`; the CI supply's
  `Dockerfile` and its `.dockerignore` join them, and `docker buildx` still validates them.
- The configuration reference lists, for each format, who decides its blank lines.
- The Unreleased section of `CHANGELOG.md` gains a line.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: ADDED `Text without a native formatter has one canonical layout`.

## Impact

A new pure module in `src/ethos/repository/paradigm/`, `src/ethos/adapters/gates/formatting.py`,
the pre-commit hook, `.config/checks/format-selection/policy.toml`,
`docs/reference/configuration.md`, their tests and `CHANGELOG.md`.
