# Quality Gate Design

Use this reference when strengthening ETHOS quality gates without turning CI,
hooks, or tool configuration into a second truth center.

## Gate Owner Model

A gate is active only when all owner surfaces agree:

1. `system/tools.toml` records why the gate exists, its profile, config owner,
   and reusable execution surface.
2. Tool-native policy lives under the smallest stable owner, usually
   `.config/checks/<concern>/` or a root-native file when the tool requires root
   discovery.
3. `tools/ci/scripts/` owns reusable execution commands.
4. Hosted CI and hooks invoke owner scripts or ETHOS command surfaces; they do
   not restate policy inline.
5. Tests or proof commands assert the contract so drift becomes visible.

If one of those surfaces is missing, classify it as design debt rather than
papering over the runner.

## Current Hard Quality Floor

The product hard floor is intentionally compact:

- Ruff check and Ruff format check run from `tools/ci/scripts/run-python-lint.sh`.
- The Ruff ignored-rule ratchet is part of the same Python lint proof surface.
- Ty policy lives in `.config/checks/ty/policy.toml`; zero-tolerance packages may
  not emit diagnostics and ratchet packages may not exceed their baseline.
- Unit and architecture tests run with branch coverage through
  `tools/ci/scripts/run-python-tests.sh`.
- Coverage configuration lives in `.config/checks/coverage/coverage.ini`; the
  current hard floor is read from `.config/checks/coverage/policy.toml`, mirrored
  by `coverage.ini`, and branch coverage is required.
- Public-surface docstring policy lives in `.config/checks/docstrings/policy.toml`
  and is executed by `tools/ci/scripts/run-docstring-coverage.sh`.
- TOML/YAML config lint, shell lint, import boundaries, security, and link checks
  are separate gates with separate owners.

## Root Configuration Boundary

Root configuration is allowed only when the tool or substrate requires root-native
discovery and no explicit owner path can preserve the same behavior. `pyproject.toml`
stays package/workspace metadata. Ruff and pytest are owned explicitly by
`ruff.toml` and `.config/checks/pytest/pytest.ini`; owner
scripts pass those paths, so repository root `ruff.toml` and `pytest.ini` are
stale-root pollution rather than admitted owners.

## Tightening Rule

Tightening means moving a late failure upstream in this order:

```text
incident -> diagnosis -> config owner -> script owner -> hook/CI projection -> proof gate -> schema/default
```

Do not add a hosted CI command when a local owner script or ETHOS command can own
that behavior. Do not add a new gate if an existing gate can expose the same
concern with clearer evidence.
