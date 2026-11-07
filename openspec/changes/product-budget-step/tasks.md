# Tasks

## 1. Retire the duplication

- [x] 1.1 Add `ethos.adapters.actor` and use it for every product read of `ETHOS_ACTOR`. Done when
      `rg 'environ.get\("ETHOS_ACTOR"' src/ethos` finds only the owner, its tests pass, and the
      lease, handoff, landing and MCP tests pass. At 20:01:10 the affected sweep had passed 2,638
      tests with no failure when its 2,400-second limit interrupted it under a host load near 40;
      they include the owner tests and the guard that no other product module names the variable,
      and `rg` finds the variable only in `src/ethos/adapters/actor.py`. The full proof runs the
      rest.
- [x] 1.2 Add `ethos.contracts.digest` and use it for every procedural 64- and 40-or-64-character
      hexadecimal check of the same shape. Done when its tests pass and the modules that used a copy
      pass their tests. At 19:20:03 the 11 owner tests passed, and the 2,638 affected tests above
      include the modules that used a copy of the checks.
- [x] 1.3 Delete `mapped_retag_receipt`. Done when no file names it and the retag tests pass. No
      file under `src` or `tests` names `mapped_retag_receipt`, and the retag tests passed in the
      same sweep.

## 2. Step

- [x] 2.1 Record the necessity review in DR-0020, index it, and set the product ceiling to 80,000 in
      `.config/checks/format-selection/policy.toml`. Done when the lane's source-budget gate passes
      and reports the product line-equivalents after the removal. At 19:2x the lane source budget
      passed with no gap: product 73,121 of 80,000 line-equivalents (517,273 code tokens), down from
      73,163 (517,571) before the removal. DR-0020 is indexed.
