# Tasks

## 1. One fixture construction authority

- [x] 1.1 Add `RepositorySpec` and `build`, and turn rows 1 to 5 into presets over them. Done when
      the stage bodies they replace are deleted, the signature and proof fixtures build through a
      spec, and the enforced `python_tests` figure does not grow. In `2d0b08123`: `RepositorySpec`
      and `build` hold the stage code, `init_git_repo`, `start_adopted_candidate` and
      `prepared_work_lane` are one-expression presets over them, and the signature and proof
      fixtures build through a spec. The enforced `python_tests` reads 99,899 before and after
      (tokens +0, effective lines -2).

## 2. Acceptance

- [x] 2.1 Pass the tests that import the changed support modules, the architecture tests, the
      precheck and readiness at the lane head. Done when each passes on the committed head. In a
      scratch clone at the same support code, 14 shards covering 290 test targets,
      `tests/architecture` included, passed 5,208 tests; in the lane at `2d0b08123`,
      `tests/architecture` passed 292 tests and the static precheck passed; readiness passed 28 of
      28 gates at `e59dcb159`.
