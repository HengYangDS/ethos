# Proposal

## Why

ETHOS fixes one Python version for every repository it governs. The paradigm requires each
`pyproject.toml` to declare a lower bound of exactly 3.12 and each Ruff carrier to target `py312`.
The owner said, as relayed on 2026-11-26, that this lock is wrong and that each governed repository
declares its own configuration, and placed the change in the batch tagged on 2026-12-05.

Today a repository that moves to Python 3.14 is refused twice: its `requires-python` is not 3.12,
and its Ruff carrier is not `py312`. A carrier at `py314` also makes the format check refuse every
file that Ruff writes differently at 3.12 and 3.14, because the shipped settings run at 3.12 beside
it.

## What Changes

- The Python module names the manifest key that declares its version,
  `version_key = "project.requires-python"`, instead of a fixed `floor = "3.12"`. Any single `>=`
  clause that names a version conforms; a missing or malformed one is still a `module-floor` gap.
- The Ruff formatter row keeps `line-length = 100` and declares `target-version` as a key the
  carrier sets to a value of its own. While it is absent the gap and its repair are today's
  (`py312`).
- When the shipped and the repository's Ruff settings render a Python file differently, the
  render runs both again at the target the repository's carrier declares, and the file passes when
  they then agree. Every render that passes today is unchanged.

This release may only admit: nothing that passes on the predecessor is refused. One reader of
`requires-python` for every runner, refusing Python with no declared target, and a carrier target
that differs from the lower bound each change a verdict, so each is left to a release after 0.2.0,
where it is reported for one release first.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: "Configured formatters share one width" and "Ecosystem modules lock their
  manifests" no longer fix Python 3.12.

## Impact

Every governed repository read on 2026-11-27 declares `>=3.12` and either carries `py312` or no
carrier, so none changes when this ships. A repository that moves to 3.14 sets
`requires-python = ">=3.14"` and its carrier's `target-version = "py314"` in one commit and
reformats in the next; the commit hook formats the first under the parent's carrier.
