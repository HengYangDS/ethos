# Proposal

## Why

Native pre-commit admission checks staged Python with Ruff only when the index or `HEAD` tracks the
repository's own `.config/checks/ruff/ruff.toml` (`_check_staged_python_format` in
`src/ethos/adapters/repo/hook/admission.py`). That carrier is optional: the repository-paradigm
requirement "Text formatting uses the shipped common formatters" runs the formatters on the shipped
settings when a repository keeps none, and the `format_check` gate always checks Python with the
shipped Ruff policy (`native_configurations` in `src/ethos/adapters/gates/native/inputs.py`). A
repository without the carrier therefore commits Python that its own proof then refuses.

- On 11-03 Codex qualified this in di-effect, which keeps no Ruff carrier, under the alpha.28
  runtime: `git hook run pre-commit` exited 0 for an unformatted staged `tests/_factories.py`,
  while Ruff with the runtime's shipped settings exited 1 for the same blob.

## What Changes

- The staged Python format check uses the repository's own Ruff carrier when the index or `HEAD`
  tracks one, as it does now, and the shipped Ruff settings when neither does.
- A shipped input that a source runner reads beside its package, and an installed runtime verifies
  against its distribution record, is resolved by one helper that the format gate and the hook
  share.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: pre-commit admission checks staged Python with the shipped Ruff settings
  when a repository configures no Ruff.

## Impact

`_check_staged_python_format` in `src/ethos/adapters/repo/hook/admission.py`, a shipped-input helper
in `src/ethos/repository/release/resources.py` that `native_configurations` also uses, the
pre-commit execution tests, the configuration reference and the changelog. Adopters without a Ruff
carrier get a staged format check on their first commit of unformatted Python after they upgrade.
