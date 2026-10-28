# Tasks

## 1. Evidence Before Deletion

- [x] 1.1 Show that the preparing, committed and aborted states leave ETHOS state, journals and attestations unchanged. Done when a protocol test that snapshots the common `ethos` directory passes before the terminal branch is removed (`test_states_other_than_prepared_leave_no_ethos_trace` passed on `a6ad56b67`).
- [x] 1.2 State the launch count as a regression. Done when the launcher test fails before the guard exists (it recorded starts for the preparing, committed and aborted states).

## 2. Governed States

- [x] 2.1 Add the one-line guard to the launcher template and accept templates with or without it. Done when the launcher test records only prepared starts, one for `update-ref`, `git hook run` shows the guard in Git's shell (it failed without the guard), and an earlier template still renders unchanged launchers.
- [x] 2.2 Answer every state other than prepared as not governed in the protocol, and remove the terminal branch. Done when the protocol and binding tests pass, and the no-trace test still passes (256 hook, runtime-binding and ref-admission tests passed).

## 3. Spec And Record

- [x] 3.1 Restate the hook requirements as "only prepared is governed" and add the launcher requirement. Done when strict validation passes and the simulated archive leaves every spec valid.
- [x] 3.2 Record the change under `[Unreleased]` in `CHANGELOG.md`, and the heavy-test CPU time before and after in the design. Done when `markdown_lint` and `prose` pass.

## Workflow follow-up

- Archive, prove once, land and publish `dev` to GitHub. Adopters pick up the launcher when they rebind with `ethos hook install`.
