# Tasks

## 1. Host Command Baseline

- [x] 1.1 Follow the locked tools with the host's own command baseline, built by one pure function. Done when a regression proves three things: POSIX keeps `os.defpath`; Windows gets `%SystemRoot%\System32`, `%SystemRoot%` and the shell-free Git launcher, without `.` or `C:\bin`; and a Git directory that holds a shell never joins (`test_host_command_baseline_is_the_host_own_command_directories`, `test_git_launcher_directory_never_brings_a_shell`; three mutants caught).

## 2. Release Entry

- [x] 2.1 Move the product version to 0.2.0-alpha.15 in `VERSION`, `distributions/npm/package.json`, its `package-lock.json` entry and the three version tests. Done when the lane's `ethos --version` reports 0.2.0-alpha.15 and those tests pass (`tests/unit/cli/test_version_command.py`, `tests/unit/release/test_version_identity.py`; `ethos --version` reports 0.2.0-alpha.15).
- [x] 2.2 Curate the `0.2.0-alpha.15` entry from this fix. Done when the changelog validates with 0.2.0-alpha.15 as its release target and the entry describes every product change since `v0.2.0-alpha.14` (`changelog_errors` with target 0.2.0-alpha.15).

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out and re-arm the root.
- The release owner publishes `dev` and `main`, checks the hosted runs on every platform, creates the signed tag with `ethos land --release` and relays the identities. DDWG's `windows-latest` verification on that release is the hosted proof.
