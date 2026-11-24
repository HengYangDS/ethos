# Tasks

## 1. The install's mode

- [x] 1.1 State the rule once and apply it in `install_locked` and in `download_tool`. Done when
      unit tests, driven by native Mise's answer to the trust query, show for both installs no safe
      mode for a trusted root and safe mode for any other, Mise's state inside the disposable copy
      and its search ended at the copy's parent in both, and resolution in safe mode as before.
      (At `693927369` `tests/unit/adapters/toolchain/test_mise_install_mode.py` passes, 10
      cases: the install for a trusted and an untrusted root, the runner in safe mode for
      both, the entry's three refusals, the provisioner in four cases and the rule alone. The
      pre-check passed there with 0 findings: 392 impacted test files, 7,672 passed, 3
      skipped. With native Mise 2026.11.9 and 2026.11.12 from the lane's code on macOS, an
      install under a CI marker took the locked build `20261110`, an install without trust
      stayed in safe mode, and a `mise.toml` above the provisioner's copy did not run.)
- [x] 1.2 Record the repair in the changelog. Done when the Unreleased section's Fixed list names
      it and the checks of the changelog pass. (The entry leads the Fixed list at `693927369`; the
      pre-check's static part reported 0 findings and the architecture tests passed, 40 files.)
- [x] 1.3 Prove the download on hosted runners. Done when the proposal ref's push run passes the
      supply step in every job with the lock unchanged and each job's installed CPython build is
      read from its log, and one typed dispatch with the Windows legs has ended with each leg's
      supply step read. (Run 45318565024 at `6bf171c04`: the supply step succeeded in all
      seven jobs, and each log names `cpython-3.14.10+20261110` for its platform: Linux x64 in
      four jobs, Linux arm64 in two, macOS arm64 in one; no file under `.config/mise` differs
      from `dev`. The run before, 45293766508, failed that step in all seven. The same run's
      quality gates failed in one test that this Change had broken,
      `tests/unit/ci/test_go_tool_supply.py`; `693927369` repairs it, and the pre-check of
      task 1.1 ran it. Dispatch 45318745669 at `6bf171c04`: the supply step succeeded on the
      four Windows legs, x64 with Python 3.12, 3.13 and 3.14 and arm64; each log names
      `cpython-3.14.10+20261110-x86_64-pc-windows-msvc`, and each leg's conformance session
      ended with 119 passed and 11 skipped.)
