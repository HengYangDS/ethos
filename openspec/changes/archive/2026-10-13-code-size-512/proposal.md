## Why

The user set the repository's effective-line ceiling to 512. That decision is already recorded in 693c15f23 on the e448cc7c line, but it never reached the accepted line: dev still declares 500. The native-outputs port deliberately left the ceiling to the accepted line's own governance. The file-size schema also rejects 512, because it requires limits to be multiples of one hundred.

## What Changes

- `.ethos/rules.toml` declares `default_effective_max_lines = 512`.
- A declared ceiling is any positive integer. The `multiple_of=100` constraint is removed from the rules configuration owner, and the quality spec stops requiring multiples of one hundred.
- The size-gate tests assert the declared 512 ceiling and keep rejecting booleans, strings, floats, zero and negative values.

## Impact

- Code: `src/ethos/repository/policy/rules/config.py`, `.ethos/rules.toml`, `tests/unit/domain/test_prove.py`.
- Specs: quality `Declared file-size policy is strict and observable`.
- Ceilings stay declared, strict and exemption-free; only the permitted value set widens.
