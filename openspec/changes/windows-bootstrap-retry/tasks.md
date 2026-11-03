# Tasks

## 1. Bootstrap

- [x] 1.1 Retry the replace while Windows holds the staged executable. Done when a test shows that
      two held attempts are waited out and the third publishes the executable, while a permission
      error without a held-file code fails on its first attempt, and the test failed before the
      change. The held case failed on its first attempt before the change; both cases and the
      native supply and changelog tests pass (118).
- [x] 1.2 Name the fix in the Unreleased notes. Done when the changelog validates. It does.
