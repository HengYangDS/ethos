# Configuration Layout

`.config/` holds tool-native configuration and hosted-runner setup. It is a
configuration plane, not a truth center.

## Separation of concerns

- `pyproject.toml` is limited to Python package/workspace metadata and uv wiring.
- `pytest.ini` is the pytest source of truth.
- `ruff.toml` is the Ruff root source of truth because Ruff resolves path globs
  relative to the config file location.
- `.config/checks/<concern>/` holds reusable tool payloads by concern.
- `.config/ci/scripts/` holds reusable runner bootstrap logic; hosted CI YAML is
  only a provider projection that calls these scripts.
- `system/tools.toml` records why each gate exists, which profile owns it, and
  where its configuration lives.

## Boundary rule

Do not duplicate the same policy in multiple files. If a provider surface needs a
policy, make it invoke the owning config or script instead of re-stating the
policy inline.
