# Configuration Layout

`.config/` holds tool-native configuration and hosted-runner setup. It is a
configuration plane, not a truth center.

## Separation of concerns

- `pyproject.toml` is limited to Python package/workspace metadata and uv wiring.
- `pytest.ini` is the pytest source of truth.
- `ruff.toml` is the Ruff root source of truth because Ruff resolves path globs
  relative to the config file location.
- `.config/checks/<concern>/` holds reusable tool payloads by concern.
- `tools/ci/scripts/run-python-lint.sh` owns the executable Python lint proof surface: Ruff check, Ruff format check, and ignored-rule ratchet.
- `.config/checks/coverage/coverage.ini` owns the Python coverage floor; `.config/checks/coverage/policy.toml` records the evidence-bound hard/aspirational boundary. Generated coverage data and XML go to `build/evidence/quality/tests/coverage/`, not `.config/`. Pytest temporary directories default outside the repository so fixture roots cannot masquerade as repository truth.
- `.config/checks/docstrings/policy.toml` owns public-surface docstring coverage.
- `.config/checks/module-layout/policy.toml` owns semantic subpackage, suffix-flat, package `__init__.py` facade, and import-alias layout policy; `tools/ci/scripts/run-module-layout.sh` is the reusable runner.
- `.config/checks/taplo/taplo.toml` owns TOML canonical formatting; `tools/ci/scripts/run-config-lint.sh` also enforces TOML/JSON parseability, no TOML trailing whitespace, and exactly one final newline for TOML/JSON.
- `.config/checks/yaml/yamllint.yaml` owns YAML linting; CI invokes it through `tools/ci/scripts/run-config-lint.sh`.
- `.config/checks/shell/.shellcheckrc` owns ShellCheck policy; `tools/ci/scripts/run-shell-lint.sh` is the runner.
- `.config/checks/markdown/.markdownlint-cli2.yaml` owns Markdown lint policy; `tools/ci/scripts/run-markdown-lint.sh` installs Node (via `install-node.sh`) and runs `markdownlint-cli2`. The gate is lint-only — it never rewrites files — so it is safe over the digest-pinned governance documents; `evidence/`, `openspec/`, generated projections, and local state are excluded by the config.
- The root `.gitleaks.toml` owns secret-scanning policy (gitleaks resolves its config from a git-discoverable location, so it stays at the root); `tools/ci/scripts/run-secrets-scan.sh` installs the pinned binary via `install-gitleaks.sh` and runs the scan. `.config/checks/secrets/README.md` records the ownership boundary.
- `tools/ci/scripts/run-repository-hygiene.sh` owns cross-file hygiene such as tracked-file size, LF endings, final newline, JSON parseability, and merge-conflict marker detection.
- `tools/ci/scripts/` holds reusable runner bootstrap logic; hosted CI YAML is
  only a provider projection that calls these scripts.
- `system/tools.toml` records why each gate exists, which profile owns it, where
  its configuration lives, and which reusable script executes it when the gate is
  active.

## Root exceptions

Some root files remain because tools or repository substrates require root-native
discovery: `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE`,
`pyproject.toml`, `uv.lock`, `pytest.ini`, `ruff.toml`, `.gitignore`,
`.gitleaks.toml`, `.pre-commit-config.yaml`, `.gitlab-ci.yml`, `package.json`, and
`package-lock.json`. These are admitted root surfaces, not permission to move
reusable gate policy back into the root.

## Boundary rule

Do not duplicate the same policy in multiple files. If a provider surface needs a
policy, make it invoke the owning config or script instead of re-stating the
policy inline.
