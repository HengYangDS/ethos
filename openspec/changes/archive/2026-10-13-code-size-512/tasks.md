# Tasks

## 1. Ceiling

- [x] 1.1 Port the ceiling hunks of 693c15f23: declare 512 in `.ethos/rules.toml`, admit any positive integer limit, and assert the 512 ceiling in the size-gate tests; verify booleans, strings, floats, zero and negative values still block.

## 2. Verify

- [x] 2.1 Run strict OpenSpec validation, Ruff, ty and the size-gate and rules unit tests; verify they pass and no unrelated tracked file changed.

## Workflow follow-up

- Prove the exact head, archive this Change, prove again, then land, close out, reinstall the hook runtime and publish to GitHub.
