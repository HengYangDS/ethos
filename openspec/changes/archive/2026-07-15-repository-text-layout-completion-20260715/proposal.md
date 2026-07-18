## Why

The repository has several formatter-specific blank-line rules, but no single
contract explains their common structural meaning or checks the remaining
non-native carriers. Active GitLab YAML currently contains redundant blank
lines, demonstrating that the intended rule is not consistently enforced.

## What Changes

- Define one structural layout contract: one blank line separates adjacent
  semantic blocks; no leading, trailing, or repeated blank-line runs.
- Retain language-native formatters as authorities for Python, Markdown, TOML,
  and YAML; add a narrow shared checker only for unowned active text carriers.
- Repair active GitLab template/projection drift and document the exceptions
  that belong to embedded languages and immutable historical records.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: subject=repository-text-layout; reuse=extend; change=modify;
  facet:lifecycle=validation; facet:surface=config,ci,docs,openspec,test;
  facet:authority=source,test,docs,openspec,claim,evidence

## Out Of Scope

- Replacing Ruff, markdownlint, Taplo, Yamllint, or ShellCheck with a second
  universal formatter.
- Reformatting archived OpenSpec records or digest-pinned evidence.
- Using blank-line style as a substitute for lifecycle, proof, or provider
  publication governance.

## Impact

Quality configuration and owner scripts, a small structural checker and its
regressions, GitLab provider projections, canonical documentation, the quality
specification, and a measured temporary source-budget debt record. The declared
maximum increases only by that record's exact 190-line allowance and does not reset the
baseline or normalize existing debt.
