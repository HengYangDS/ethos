# Tasks

## 1. Coverage

- [x] 1.1 Test that an unparseable lock and a sidecar outside the repository refuse with
      `locked_toolchain_invalid` and `mise_lock_sidecar_outside_root:<directory>`, that a `settings`
      value that is not a table refuses, and that an aliased configuration carries no trust. Done
      when the toolchain tests pass and reach every line of `mise_lock.py` but its type-only
      import. At 22:16: 96 passed, and only that import is unreached.
