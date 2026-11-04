# Proposal

## Why

ETHOS resolves a repository's locked tools through native Mise in safe mode. The answer can be
wrong without any error:

- When a declared tool is not installed at its locked version, `mise which npm` exits 0 with no
  stderr. It returns another tool's executable, for example Node's bundled npm instead of the
  locked `npm:npm`.
- `locked_tool` returns that executable, so a gate can run the wrong npm and still pass.
- `locked_environment` fails closed today only because Mise warns on stderr when another version of
  the missing tool is installed. In a fresh store that warning is absent.

The isolated experiment of 2026-11-04 shows both failures. Mise 2026.11.0, and 2026.10.25 with an
untrusted root, report aigw-cli's locked npm as `installed=false` while `which` returns Node's
npm (`build/runtime/work/locked-supply-completeness/scratch-1104/logs/`). A wrong tool can admit a
wrong proof, and that blocks beta.

Mise 2026.11.0's safe mode also no longer uses the dependency graph a lock entry references
(jdx/mise#15363). The refusal's current next action, `mise trust`, does not help there.

## What Changes

- Before `locked_tool` and `locked_environment` return, native `mise ls --current --json`, run
  offline in the same isolated safe-mode resolution, must report every declared tool installed at
  its locked version with an existing install path. A missing tool is the named gap
  `mise_supply_incomplete:<tool>@<version>`.
- An executable that a declared tool provides under its own name must resolve inside that tool's
  install path. This holds for `locked_tool`'s result and for the first match on the environment's
  PATH. Otherwise the gap is `mise_executable_outside_tool:<name>`.
- The refusal names the next action that can help:
  - when the selected Mise is 2026.11.0 or later and the missing tool's lock entry references a
    dependency graph, it names that regression and an earlier Mise;
  - when the root is untrusted, `mise trust`;
  - otherwise, `mise install --locked`.
- Mise 2026.11.x is not refused as such. openai-responses-proxy runs it in CI and passes, because it
  declares no npm tool.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: locked supply must be complete before ETHOS uses it, and a refusal names `mise trust`
  only where trust can select the locked install.

## Impact

- `src/ethos/adapters/toolchain/mise.py`
- the toolchain adapter tests, and the fakes in the gate, adoption, materialization and CI delivery
  tests that answer `run_mise`
- `CHANGELOG.md`
- adopters: aigw-cli stays on Mise 2026.10.25, and the proxy is unaffected (AIGW, 11-04).
