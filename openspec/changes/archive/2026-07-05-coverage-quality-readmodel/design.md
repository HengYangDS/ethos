## Context

The official OpenSpec boundary is `ethos-quality`. The repository truth boundary
is the existing owner split: coverage policy under `.config/checks/coverage/`,
execution through `.config/ci/scripts/run-python-tests.sh`, and tool catalog
ownership in `system/tools.toml`.

## Design

`ethos quality coverage --json` is read-only. It reads:

- `.config/checks/coverage/policy.toml`
- `.config/checks/coverage/coverage.ini`
- `.config/checks/coverage/coverage.xml` when present

The command emits:

- hard and aspirational floors from policy;
- `fail_under`, branch coverage, source paths, and owner script;
- latest artifact path, line-rate, branch-rate, and line percentage when XML is
  present;
- required gaps for missing policy/config, mismatched hard floor, branch coverage
  disabled when policy requires it, missing latest artifact, malformed artifact,
  or latest coverage below the hard floor.

This keeps concerns separated: CI/proof runs tests, coverage config owns tool
policy, and ETHOS exposes the read model for agents and humans.

## Alternatives

Running tests inside `ethos quality coverage` would duplicate the proof gate and
make a read command unexpectedly expensive. Storing coverage policy in
`pyproject.toml` would violate the existing configuration boundary. Leaving the
surface absent would keep an active gate hidden.

## Proof Strategy

- Unit-test the command for clean and gapped reports using temporary policy,
  config, and XML fixtures.
- Update the canonical quality help test.
- Validate OpenSpec lifecycle and run focused proof gates.
