# Tasks

## 1. Selection

- [x] 1.1 Add `selected_change` to the selection owner. Done when a test shows that an explicit
      Change reaches in-process readers and a child process, and that the inherited `ETHOS_CHANGE`,
      or its absence, returns after a normal or failed invocation. At 21:52:30
      `test_an_explicit_change_binds_one_invocation_and_its_children` passed with an inherited
      `outer` and with no inherited value: the explicit Change reached `requested_change()` and a
      child started through `run_command`, and the inherited input returned after the invocation
      raised.
- [x] 1.2 Bind `change` in the status, plan and land operations and in the `prove` and
      `lane prewrite` commands, and add `--change` to `status`, `land` and `lane prewrite`. Done
      when tests show that in a lane with two active Changes the option wins over `ETHOS_CHANGE` for
      prewrite, status and land, and that the MCP `status`, `plan` and `land` tools accept `change`
      and leave no selection behind. At 22:08:56 the 929 tests of the admission, OpenSpec, MCP, land
      and selection suites passed. Among them, `lane prewrite --change fixture-change` admitted the
      path that `ETHOS_CHANGE=second-local` alone refused with `openspec_change_path_mismatch`;
      `status --change fixture-change` attributed it to `fixture-change` where the inherited
      selection named `second-local`; `land --change fixture-change` previewed `pass` where the
      inherited selection reported `proof_not_proven`; and the MCP `status`, `plan` and `land` tools
      exposed `change`, a call with `change=missing` reported
      `openspec_requested_change_missing:missing`, and no `ETHOS_CHANGE` remained after it.
- [x] 1.3 Name both selection inputs in the two remedies that said only `unset ETHOS_CHANGE`. Done
      when no remedy in `src/` names the variable alone. At 22:09:13 a search of `src/` found
      `unset ETHOS_CHANGE` only in those two remedies, which now read "omit --change and unset
      ETHOS_CHANGE".

## 2. Documentation and acceptance

- [x] 2.1 Document the option in `docs/reference/command-plane.md`. Done when the docs gates pass.
      At 22:18:01 the readiness tier passed its 28 gates at `f925de964`, among them `docs-registry`,
      `markdown-lint`, `markdown-links`, `prose` and `source-format`.
- [x] 2.2 Pass lint, the focused tests and readiness at the lane head. Done when each passes on the
      committed head. The first readiness, at `285148e63`, found `surface/cli/root/proof.py` at 505
      effective lines, over the per-file ceiling of 500; `prove` now binds and calls `_prove`, and
      the module measures 498. At 22:15:57 ruff, the format check and ty passed and 205 prove,
      merge-selection and change-selection tests passed, and at 22:18:01 the 28 readiness gates
      passed at `f925de964`.
