## Why

The repository-owned Python test gate passes its full configuration explicitly,
but a human or IDE may invoke pytest from the repository root without that
owner-script argument. With no root discovery metadata, pytest then creates
denied root `.pytest_cache` residue. The cache route is already singular and
semantic; discovery must converge on it without copying test policy into a
second configuration surface.

## What Changes

- Declare one root pytest discovery adapter in `pyproject.toml` containing only
  `cache_dir = "build/runtime/tool-cache/pytest"`.
- Keep strict options, markers, Python paths, timeout, coverage, JUnit, and
  test selection exclusively in `.config/checks/pytest/pytest.ini` and its
  owner script.
- Record the narrow adapter boundary in the configuration guide, quality
  requirement, and architecture regressions.
- Run the quality-audit public CLI projections through the workspace runtime, so
  an initially unsynced environment cannot falsely report missing `ethos`.

## Capabilities

### Modified Capabilities

- `quality`: subject=root-pytest-discovery-cache-route; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=config,docs,test,openspec,evidence;
  facet:authority=source,test,docs,openspec,claim,evidence

## Impact

- `pyproject.toml`
- configuration guide and quality specification
- focused configuration, architecture, and quality-audit regressions

## Out Of Scope

- Moving pytest policy, test selection, timeout, coverage, JUnit, or evidence
  routing into `pyproject.toml`.
- Changing the Python test owner script, CI projections, hooks, gate registry,
  package dependencies, or cache-cleanup behavior.
- Adding a compatibility `pytest.ini`, a second pytest policy owner, benchmark,
  Allure, performance, or remote-publication surface.
