# Tasks

## 1. Refresh Locks

- [x] 1.1 Run `uv lock --upgrade`; verify pre-commit 4.7.0 and truststore 0.10.5 are locked, `uv lock --check` passes and `uv tree --outdated` lists no package that the declared ranges admit at a newer version.
- [x] 1.2 Run `npm update --package-lock-only`; verify `npm ci` installs the lock and `npm outdated --all` lists only packages bundled inside npm, newer majors outside dependents' ranges, or versions a dependent pins exactly, such as markdownlint 0.41.1's string-width 8.2.1 and micromark-core-commonmark 2.0.3.

## 2. Verify

- [x] 2.1 Run strict OpenSpec validation and the Markdown lint; verify only `uv.lock`, `package-lock.json` and this Change changed.

## Workflow follow-up

- Prove the exact head, archive this Change, prove again, then land, close out, reinstall the hook runtime and publish to GitHub.
