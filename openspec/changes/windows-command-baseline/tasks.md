# Tasks

## 1. Host Command Baseline

- [ ] 1.1 Follow the locked tools with the host's own command baseline, built by one pure function. Done when a regression proves three things: POSIX keeps `os.defpath`; Windows gets `%SystemRoot%\System32`, `%SystemRoot%` and the shell-free Git launcher, without `.` or `C:\bin`; and a Git directory that holds a shell never joins.

## Workflow follow-up

- Prove the exact head, archive this Change and prove again. Land after Codex 019f4fbf's landing, refreshed onto its result. Then the release owner cuts the next release, and DDWG's `windows-latest` verification gives the hosted proof.
