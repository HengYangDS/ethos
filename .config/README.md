# Configuration Layout

`.config/` holds tool-native configuration and hosted-runner setup. It is a
configuration plane, not a truth center.

## Separation of concerns

- `pyproject.toml` is limited to Python package/workspace metadata and uv wiring.
- `pytest.ini` is the pytest source of truth.
- `ruff.toml` is the Ruff root source of truth because Ruff resolves path globs
  relative to the config file location.
- `.config/checks/<concern>/` holds reusable tool payloads by concern.
- `.config/ci/scripts/run-python-lint.sh` owns the executable Python lint proof surface: Ruff check, Ruff format check, and ignored-rule ratchet.
- `.config/checks/coverage/coverage.ini` owns the Python coverage floor; `.config/checks/coverage/policy.toml` records the evidence-bound hard/aspirational boundary. Generated coverage data and XML go to `build/evidence/quality/tests/coverage/`, not `.config/`. Pytest temporary directories default outside the repository so fixture roots cannot masquerade as repository truth.
- `.config/checks/docstrings/policy.toml` owns public-surface docstring coverage.
- `.config/checks/taplo/taplo.toml` owns TOML canonical formatting; `.config/ci/scripts/run-config-lint.sh` also enforces TOML/JSON parseability, no TOML trailing whitespace, and exactly one final newline for TOML/JSON.
- `.config/checks/yaml/yamllint.yaml` owns YAML linting; CI invokes it through `.config/ci/scripts/run-config-lint.sh`.
- `.config/checks/shell/.shellcheckrc` owns ShellCheck policy; `.config/ci/scripts/run-shell-lint.sh` is the runner.
- `.config/ci/scripts/run-repository-hygiene.sh` owns cross-file hygiene such as tracked-file size, LF endings, final newline, JSON parseability, and merge-conflict marker detection.
- `.config/ci/scripts/` holds reusable runner bootstrap logic; hosted CI YAML is
  only a provider projection that calls these scripts.
- `system/tools.toml` records why each gate exists, which profile owns it, where
  its configuration lives, and which reusable script executes it when the gate is
  active.

## Root exceptions

Some root files remain because tools or repository substrates require root-native
discovery: `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, `pyproject.toml`,
`uv.lock`, `pytest.ini`, `ruff.toml`, `.pre-commit-config.yaml`, `.gitlab-ci.yml`,
`package.json`, `package-lock.json`, and `justfile`. These are admitted root
surfaces, not permission to move reusable gate policy back into the root.

## Boundary rule

Do not duplicate the same policy in multiple files. If a provider surface needs a
policy, make it invoke the owning config or script instead of re-stating the
policy inline.
