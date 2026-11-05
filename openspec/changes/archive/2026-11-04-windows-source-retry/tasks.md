# Tasks

## 1. Source checkout retry

- [x] 1.1 Set `GET_SOURCES_ATTEMPTS: "3"` on generated Windows verification jobs and refuse a
      runner override. Done when the model test expects the variable on Windows jobs only, a
      runner that declares another value fails compilation, both tests failed before the change,
      and `lane project --check` reports the projections conforming. Both failed before; the 11
      model tests pass, `cue fmt --check` is clean and the projections conform.

## 2. Specification

- [x] 2.1 Write the `quality` delta. Done when strict validation and the cumulative archive
      simulation pass. Both pass; after the lane's three Changes, all 12 specifications are valid.
