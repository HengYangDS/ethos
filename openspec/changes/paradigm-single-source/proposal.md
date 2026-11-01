# Proposal

## Why

The repository paradigm asks repositories to copy facts that already have one owner, and refuses a
checked copy that a native tool needs.

- It requires a tracked Prettier, Taplo and Ruff carrier for every formatted carrier class
  (`src/ethos/repository/paradigm/report.py:343-349`), although the native gates already run on the
  configuration ETHOS ships and add a repository's own file as an increment
  (`src/ethos/adapters/gates/native/inputs.py:226-234`). The duplicated copies sit in 8 of the 11
  governed repositories (GitHub issue #20).
- It refuses any root `package.json` `version` (`report.py:426-436`), although npm needs a literal
  version to pack and publish. A repository that publishes one npm package from its root therefore
  cannot keep `VERSION` as its source; archpub keeps its manifest one level down only for this rule.

## What Changes

- A formatted carrier class needs no local formatter carrier. The shipped configuration is the
  common baseline; a repository's own carrier is an optional increment that the paradigm still holds
  to the common settings.
- A root `package.json` `version` that equals `VERSION` is a checked projection of the one version
  source. A different value, or a version without `VERSION`, is still a second source.
- `ethos repair` no longer creates formatter carriers; it still corrects a carrier's settings.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: text formatting uses the shipped formatters without a required local copy,
  and a released product's npm manifest may project `VERSION`.

## Impact

`src/ethos/repository/paradigm/report.py`, `src/ethos/repository/paradigm/repair.py`, their tests
and the `repository-paradigm` specification. No repository gains a gap: one that keeps an identical
copy still passes and may delete it.
