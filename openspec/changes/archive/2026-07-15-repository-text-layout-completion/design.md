## Context

One semantic separation is expressed differently by native tools: Ruff owns
Python, markdownlint owns Markdown, Taplo owns TOML, and Yamllint owns YAML.
Those tools do not cover every active configuration, template, and Shell
carrier. A universal formatter would either duplicate their authority or
misinterpret embedded languages.

## Goals / Non-Goals

**Goals:** make the one-blank-line structural law explicit; use native tools
where they apply; check only the remaining active text carriers; and keep
diagnostics line-addressed.

**Non-Goals:** reformat archives or digest-pinned evidence; impose Python
spacing through a second checker; or reinterpret heredoc bodies as Shell.

## Decisions

- One blank line separates semantic blocks. Two or more blank lines, and
  leading or trailing blank lines, are invalid in governed active text files.
- Native formatters remain authoritative: Ruff uses Python's PEP 8 layout;
  Markdown/TOML/YAML use MD012, Taplo, and Yamllint respectively. Official
  OpenSpec owns its schema shape; the shared reader checks only its blank runs.
- The shared reader covers active JSON, INI, Jinja, and Shell carrier spacing,
  masks Shell heredoc bodies, and does not scan evidence or archived Changes.
- Provider template and generated projection remain parity-equal.
- The small additive reader and regression set are bound to a named temporary
  source-budget debt record. The immutable maximum rises by exactly its 190-line
  allowance; its deletion wave must consolidate owner wiring rather than
  normalize permanent layout exceptions.

## Risks / Trade-offs

- [A generic reader duplicates a native rule] → scope it only to carriers not
  already checked by a native blank-line formatter.
- [An embedded body is falsely rejected] → mask heredoc payload lines while
  checking the Shell structure around the delimiter; embedded-language tooling
  remains a separate owner.
