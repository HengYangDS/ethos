---
subject: governance:repository-text-layout
role: policy
state: canonical
relations:
  implements: openspec/specs/quality/spec.md
  owner: ethos-quality-gate-governance
---

# Repository Text Layout

Status: canonical.

Purpose: define one structural meaning for blank lines without replacing each
language's native formatter.

See also: [Quality Specification](../../openspec/specs/quality/spec.md),
[Config Boundary Model](config-boundary-model.md), and
[Product Design Contract](product-design-contract.md).

## Rule

One blank line separates adjacent semantic blocks. Do not add a blank line at
the beginning or end of a text carrier. Do not use two or more blank lines as
visual padding.

## Owner Matrix

| Carrier | Owner | Blank-line rule |
| --- | --- | --- |
| Python | Ruff | PEP 8: two blank lines between top-level definitions; one inside a class or method body when separating semantic blocks. |
| Markdown | markdownlint MD012 | One blank line between block elements; never repeated blank runs. |
| TOML | Taplo | At most one blank line between tables or semantic groups. |
| YAML | Yamllint `empty-lines` | At most one blank line; none at start or end. |
| JSON, INI, Jinja, plain text/DLS | Structural whitespace reader | One blank line only between semantic groups. |
| Shell | ShellCheck plus structural reader | One blank line between command/function blocks; heredoc payloads are excluded from Shell layout and retain their embedded language's own rule. |
| Active OpenSpec Markdown | Official OpenSpec plus structural reader | Official schema owns the wider shape; the shared reader rejects repeated blank runs only. |

Historical evidence and archived OpenSpec changes are immutable carriers. Active
OpenSpec specs and Changes remain under the official OpenSpec schema rather than
the repository's general Markdown style rules, while the shared reader applies
the universal one-blank-line boundary.

## Use

Run the owner scripts rather than copying policy into a provider file:

```bash
tools/ci/scripts/run-config-lint.sh
tools/ci/scripts/run-markdown-lint.sh
tools/ci/scripts/run-shell-lint.sh
```

The common reader is available for focused diagnostics:

```bash
python tools/ci/structural_whitespace.py <repository-relative-path>
```
