# Tasks

## 1. Typing

- [x] 1.1 Remove the type-ignore from the binary scan report builder. Done when repository hygiene
      and the type checker pass on the file and the binary scan tests pass. Repository hygiene,
      which stopped `b2p1`, finds no suppression; ty passes on the file; the 4 binary scan tests
      pass. Correction to `batch-2-integration` task 1.1: the binary scan module has 4 tests, not
      36; the 38 tests then also counted the 34 of the two architecture modules.
