# Tasks

## 1. Retire the duplication

- [ ] 1.1 Add `ethos.adapters.actor` and use it for every product read of `ETHOS_ACTOR`. Done when
      `rg 'environ.get\("ETHOS_ACTOR"' src/ethos` finds only the owner, its tests pass, and the
      lease, handoff, landing and MCP tests pass.
- [ ] 1.2 Add `ethos.contracts.digest` and use it for every procedural 64- and 40-or-64-character
      hexadecimal check of the same shape. Done when its tests pass and the modules that used a copy
      pass their tests.
- [ ] 1.3 Delete `mapped_retag_receipt`. Done when no file names it and the retag tests pass.

## 2. Step

- [ ] 2.1 Record the necessity review in DR-0020, index it, and set the product ceiling to 80,000 in
      `.config/checks/format-selection/policy.toml`. Done when the lane's source-budget gate passes
      and reports the product line-equivalents after the removal.
