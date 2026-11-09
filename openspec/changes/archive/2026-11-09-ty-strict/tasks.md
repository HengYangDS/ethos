# Tasks

## 1. Selection

- [x] 1.1 Declare `all = "error"` with the four owned deferrals. Done when ty loads the selection
      and the ty gate's test pins the ignored set by equality. `.config/checks/ty/ty.toml` declares
      `all = "error"` and ignores exactly the four owned rules. At `9189adac5`, ty loaded it at
      05:48:31, and the 15 tests of `test_ty.py` passed from 05:04:06 to 05:04:10,
      `test_ty_selection_raises_every_rule_but_the_owned_deferrals` pinning the ignored set by
      equality among them.

## 2. Fixes

- [x] 2.1 Fix every finding of the selection. Done when ty passes over the configured include set
      and Ruff passes. At `9189adac5`, ty passed over the configured include set and
      `ruff check --no-cache` over `src`, `tests` and `tools`, both at 05:48:31. The 95 findings
      measured at `9d0a8576d` are fixed, along with the 57 downstream findings that typing the bare
      `dict`s first exposed.
- [x] 2.2 Type the Nox sessions with the `Session` protocol and one typed test double. Done when no
      test casts a double to a session and one typed binding checks the real session's conformance.
      `tools/ci/session.py` declares the `Session` protocol, and its `_conforms` binding has ty
      check `nox.Session` against it. At `fd2b9c9d2` no test casts to `nox.Session`, and the two
      converted test files passed 30 tests from 06:11:10 to 06:11:14.

## 3. Acceptance

- [x] 3.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there. The precheck passed with 0 findings at 05:48:29 at `9189adac5`, and
      readiness passed 29 gates from 06:11:54 to 06:13:12 at `fd2b9c9d2`. The impacted sweep of 403
      test files ran from 05:06:42 to 05:46:46 on the Change's uncommitted tree: 7761 passed and 2
      skipped. `local-install-smoke` passed from 05:49:21 to 06:00:09 and `release-sbom` from
      06:00:09 to 06:10:15, both at `9189adac5`.
