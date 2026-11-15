# Proposal

## Why

A review of the release diff (`v0.2.0-beta.10..dev`: product, tools and configuration) on
2026-11-15 returned findings against the pin work that 0.2.0-beta.11 ships first; its tag is
planned for 2026-11-21. Each finding was treated as a lead and tested through the public seam of
its module before any code changed. Three leads hold, in whole or in part, and all three concern
behavior that no release has shipped:

- With nothing selected, `ethos adopt --select-runtime` refuses an accepted pin that it cannot
  select (`runtime_pin_unattested`, `runtime_pin_not_installed`), and its next action is the same
  request, which meets the same refusal. The plan holds the refusal's own repair, for example
  `mise --cd <root> install --locked`, and the result ignores it. The scenario
  `The pinned release is not installed` of `Runtime activation follows the accepted pin forward`
  already requires that repair as the next action.
- The same command selects a pinned install without the declaration preflight that hook
  activation runs before it pins anything. The scenario `A newer pin is installed` of the same
  requirement names the preflight for both commands. Activation's other check, the validation of
  the install, already reaches adoption through the functions it calls.
- `ethos adopt --exit` plans no pin in three different states: the repository holds none, the
  Mise configuration cannot be read, or the bare pin is not a line of its own. In the last two the
  exit applies and reports `applied` while the pin that adoption wrote stays, and nothing in the
  plan says so.

## What Changes

- A refused runtime selection continues with the refusal's own next action.
- The adoption plan probes a pinned install against the root's publication declaration before any
  effect, and refuses as hook activation does. One function beside the preflight owns that check,
  and both commands call it.
- The preflight's refusal ends with "repeat this request with `--root <lane>`", which holds for
  both commands; it named `hook install`.
- The exit plan's `pin` names a configuration that the exit keeps, with the reason under `kept`,
  and the apply writes only a text that the plan names. The applied result's next action names
  the kept file and the reason before the status command.
- The adoption architecture page and the changelog say the same.

Not breaking: adoption's pin following and the exit's pin removal are unreleased. For
`ethos hook install` only the last clause of the preflight's next action changes; its gap, verdict
and exit stay.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtime-activation`: MODIFIED requirement `A repository exit is previewed before any effect`.
  Its text names only the pin that the exit removes, and its scenario promises the text without
  the pin's line for every bare pin.

## Impact

`src/ethos/application/adoption.py`, `src/ethos/adapters/repo/adoption.py`, and under
`src/ethos/adapters/repo/hook/`: `rollback.py`, `activation.py`, `exit_plan.py` and `exit.py`.
Tests: `tests/unit/adapters/repo/runtime/test_pin_selection.py`, `tests/unit/adoption/test_pin.py`,
and the patch targets of two tests in `tests/unit/adapters/repo/hook/`. Documents:
`docs/architecture/adoption-profiles.md` and `CHANGELOG.md`.
