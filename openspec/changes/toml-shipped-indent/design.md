# Design

## Context

See the [proposal](proposal.md). `tomli_w.dumps` takes an `indent` argument since 1.1, and the
shipped Taplo policy keeps arrays open (`array_auto_collapse = false`) with a trailing comma, so a
multi-line array that `tomli_w` writes with the policy's indent is already in Taplo's layout.

## Goals / Non-Goals

Goals: TOML that ETHOS writes into a governed repository is byte-equal to what the shipped Taplo
policy would format it to.

Non-Goals:

- The packaged audit policy bytes, which other digests bind.
- Reformatting existing files.
- A repository whose Taplo file declares other `[formatting]` settings. The format gate renders
  each file with both policies, so any array refuses `native_formatter_policy_conflict` there,
  whatever indent ETHOS writes, until the repository takes the shipped settings.

## Decisions

1. `src/ethos/repository/toml_layout.py` owns the renderer. It reads the indent from
   `.config/checks/taplo/taplo.toml` through `canonical_resource`, so the Taplo policy stays the
   indent's only owner, and an `indent_string` that is not spaces alone refuses
   `taplo_indent_not_spaces`.
2. Every `tomli_w.dumps` that writes a governed file calls the one renderer: three sites in the
   paradigm repair and the profile renderer that `ethos adopt` uses. A test runs the shipped Taplo
   over a rendered profile with two arrays and finds nothing to change.

## Risks / Trade-offs

None beyond layout: a repository that formatted the four-space output by hand keeps its file until
the next repair rewrites it.
