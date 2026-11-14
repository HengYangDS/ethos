# Tasks

## 1. The isolation

- [x] 1.1 Declare `MISE_ENVIRONMENT_PREFIXES` in `src/ethos/adapters/toolchain/mise.py` and use it
      at all eleven call sites. Done when `git grep -n '("MISE_",)' -- src/ethos` returns nothing
      and ruff and Ty pass.
- [x] 1.2 Add the child-environment regression to `tests/unit/adapters/toolchain/test_mise.py` and
      name both prefixes in the two assertions of the call options. Done when the three touched
      test modules pass.

## 2. Documents

- [x] 2.1 Add the Fixed line to the Unreleased section of `CHANGELOG.md`. Done when Prettier, Vale
      and codespell accept it.

## 3. Lane

- [x] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.

## Workflow follow-up

- The governed repository whose proof showed the defect proves the same archived head from an
  activated shell under the release that carries this Change; its own lane owns that run.
