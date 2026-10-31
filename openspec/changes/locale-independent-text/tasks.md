# Tasks

## 1. Reproduce the defect

- [ ] 1.1 Add a process-adapter regression in which a child writes UTF-8 text containing an em dash
      and reads UTF-8 input while `locale.getencoding()` reports GBK. Done when it fails on `dev`
      with the GBK decode error and passes after 2.1.
- [ ] 1.2 Reproduce the reported failure end to end: `ethos status --json` in a repository whose
      head subject contains an em dash, under `LC_ALL=zh_CN.GB18030`. Done when it reports the
      decode gap before 2.1 and 3.1 and passes after them.

## 2. Process text is UTF-8

- [ ] 2.1 Make `run_command` decode output and encode input as UTF-8 unless the caller declares the
      encoding its command writes, delete the locale branch of `_decoded`, and spool text input as
      UTF-8. Done when 1.1 and the process-adapter tests pass.
- [ ] 2.2 Make the Windows PowerShell trust-anchor observation and process listing set
      `[Console]::OutputEncoding` to UTF-8 without a byte-order mark first. Done when their command
      tests assert the statement and the Windows hosted tests pass.

## 3. One interpreter-flag owner

- [ ] 3.1 Add the module that names `-B -I -X utf8` and builds internal Python commands, and route
      the CLI re-exec, `runtime_command`, the hook next actions and admission runner, proof
      admission, runtime post-observation, the materialization probes, uv through supply Python,
      both console launchers and the `tools/ci/` prefixes through it. Done when no product or tool
      file spells the flags outside that module and the runtime, hook, proof-admission,
      materialization and distribution tests pass.
- [ ] 3.2 Add `-X utf8` to the npm launcher. Done when its launcher test passes.
- [ ] 3.3 Assert that a runtime child started through the owner reports `sys.flags.utf8_mode == 1`.
      Done when the test fails without the flag and passes with it.

## 4. Guards on ETHOS's own text I/O

- [ ] 4.1 Name `encoding="utf-8"` at the product, tool and test sites that Ruff's `PLW1514` reports,
      and resolve the `path-constructor-current-directory` preview finding. Done when Ruff passes
      under the configuration of 4.2.
- [ ] 4.2 Select `PLW1514` with `preview = true` and `explicit-preview-rules = true` in
      `.config/checks/ruff/ruff.toml`. Done when the lint gate passes and an implicit read in a
      fixture fails it.
- [ ] 4.3 Set `PYTHONWARNDEFAULTENCODING=1` in the test gate's environment. Done when the test gate
      passes and an implicit `open` in a test fails it with `EncodingWarning`.

## 5. Documentation and verification

- [ ] 5.1 Record the change in `CHANGELOG.md` under Unreleased. Done when the prose and docs gates
      pass.
- [ ] 5.2 Run every test module that imports a changed module. Done when they pass.
- [ ] 5.3 Measure the product source budget. Done when the Python product total is at most 70,000
      effective lines and every touched file is within 500.
