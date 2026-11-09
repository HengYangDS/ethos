# Proposal

## Why

ETHOS's own `shell-lint` gate cannot see a shell file it would judge. The shipped paradigm refuses
every tracked script that is not the recorded output of a catalogued generator, and ETHOS tracks
none. The gate therefore passes vacuously in `default` and `full`, though it is trust-bearing, and
`unit-architecture` waits on it. The shipped format ownership of shell also names ETHOS's
`shell_lint` Nox session, a command that no governed repository can run.

## What Changes

- ETHOS's `shell-lint` gate, its Nox session, its pre-commit hook and `.shellcheckrc` are removed,
  together with their documentation, Skill and test references. `unit-architecture` no longer
  depends on the gate.
- The shipped shell ownership and format rows name the paradigm's script refusal, which every
  `ethos prove` audits, instead of the removed session.
- A direct test of the session inventory helper replaces the shell case that tested it until now.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The rows changed in the shipped format policy are descriptive; no command reads them.
Formatting with shfmt is unchanged. Its retirement, which the paradigm's script rule implies, goes
with the next supply move.

## Impact

- `system/repository-gates.toml`, `tools/ci/sessions.py`, the pre-commit configuration,
  `.config/checks/shellcheck/`, `.config/checks/format-selection/policy.toml`,
  `src/ethos/repository/policy/surfaces.py`, `docs/reference/configuration.md`, the quality Skill
  and its activation entry, and `tests/architecture/test_nox_toolchain.py`.
- ETHOS's proof runs one gate fewer; no governed repository's obligations change.
