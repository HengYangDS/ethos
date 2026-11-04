# Proposal

## Why

`skill_portfolio_report` validates the records that `.agents/skills/activation.toml` lists. It never
lists the package directories under the Skills root. A registry that routes only some packages
therefore passes, while the other packages stay routed by a second, repository-local contract.
That is the partial-registry shortcut that the 2026-11-04 qualification of di-effect's Skill
migration found (gap 1). The rule that the portfolio owner is the sole validator holds only for
the packages the registry names.

## What Changes

- The portfolio report names each package directory that holds `SKILL.md` and that neither an
  active record nor a retirement routes, as `skill_package_unregistered:<directory>`.
- The check runs only when the registry itself loads, so a missing or invalid registry keeps its
  existing single gap.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `assistant-projections`: the Skill portfolio validation reports an unrouted package.

## Impact

`src/ethos/assistants/skills/portfolio.py` and `tests/unit/assistants/test_skills_public_branches.py`.
A governed repository whose registry leaves a package unrouted gains this gap. The fleet check
before landing records which repositories, if any, those are.
