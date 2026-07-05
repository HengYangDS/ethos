## Why

Coverage is already an active product-toolchain gate: `system/tools.toml`,
`.config/checks/coverage/coverage.ini`, `.config/checks/coverage/policy.toml`,
and `.config/ci/scripts/run-python-tests.sh` define the owner and proof path.
However `ethos quality coverage --json` is missing, so agents can observe the
hard floor only indirectly through proof or shell scripts. That is a projection
mismatch for an active quality floor.

## What Changes

- Add a read-only `ethos quality coverage --json` command.
- Report the configured coverage policy, source paths, branch coverage setting,
  latest XML artifact summary when present, and deterministic gaps when config
  or latest evidence is stale or below the declared floor.
- Keep execution ownership in `.config/ci/scripts/run-python-tests.sh`; the new
  command is a read model, not a second test runner.

## Capabilities

- `ethos-quality`: subject=coverage-readmodel; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=cli; facet:authority=source

## Out Of Scope

- Changing the coverage threshold.
- Replacing `.config/ci/scripts/run-python-tests.sh` as the test gate owner.
- Adding a second coverage configuration store.
