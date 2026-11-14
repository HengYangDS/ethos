# Proposal

## Why

The owner decided on 2026-11-14 that the package-docstring obligation reports and does not block
from beta.11 on. The obligation arrived in beta.10 already blocking: every tracked `__init__.py`
without an opening docstring became a required paradigm gap, with no earlier release that reported
it, no repair the product can write and no preview of its reach. Under beta.10 two governed
repositories carried 1,348 and 203 such gaps, all on empty package markers, and because a
paradigm gap blocks proof and landing, neither repository could prove or land. `pre-commit`
refused a commit that added an empty marker as well.

The owner's approved sentence for the product contract is "A new rule reports before it refuses".
Nothing in the product could carry that: a paradigm gap had one state, required. This Change gives
the paradigm the smallest carrier of the other state and puts this one obligation in it. As a
defect that blocks governed repositories it does not use the weekly off-gate row.

## What Changes

- The paradigm declares `reporting`, a list of obligation names. A gap of a listed obligation
  appears in the paradigm report with its carrier and repair and under `reported_gaps`; it is not a
  required gap, does not change the verdict and does not select the report's next action.
- `package-docstring` is the one listed obligation. `pre-commit` no longer refuses a staged
  package marker while it is listed.
- The Unreleased section of `CHANGELOG.md` gains a Changed line.

Not breaking: nothing that passed before is refused. A repository that kept its markers documented
is unaffected. The obligation's scope (which markers owe a docstring) and the release in which it
arms again are not decided here.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: MODIFIED requirements `Paradigm conformance is a blocking verdict` and
  `Python packages state their purpose`.

## Impact

`src/ethos/contracts/paradigm/paradigm.toml`, `src/ethos/contracts/paradigm/declaration.py`,
`src/ethos/repository/paradigm/report.py`, `src/ethos/adapters/repo/hook/staged_text.py`, two test
modules, `CHANGELOG.md` and `openspec/specs/repository-paradigm/spec.md` through this Change's
delta.
