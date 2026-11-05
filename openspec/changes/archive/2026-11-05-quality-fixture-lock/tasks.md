# Tasks

## 1. Fixture lock

- [x] 1.1 State that the fixture lock pins the repository's versions. Done when the new architecture
      test fails on coverage 7.17.0 against 7.17.1 and names both versions. The test failed first
      with `{"coverage": "fixture 7.17.0, repository 7.17.1"}`.
- [x] 1.2 Lock the fixture to coverage 7.17.1 with uv. Done when the new test and the 31 native Nox
      tests pass. `uv lock --upgrade-package coverage==7.17.1` changed only coverage; the new test
      and the 31 native Nox tests pass (32).
