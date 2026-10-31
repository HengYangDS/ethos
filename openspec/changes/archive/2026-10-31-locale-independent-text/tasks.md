# Tasks

## 1. Reproduce the defect

- [x] 1.1 Add a process-adapter regression in which a child writes UTF-8 text containing an em dash
      and reads UTF-8 input while the host locale is GBK. Done when it fails on `dev` with the GBK
      decode error and passes after 2.1. (Failed with `'gbk' codec can't decode byte 0x94`; passes.)
- [x] 1.2 Reproduce the reported failure end to end under `LC_ALL=zh_CN.GBK`. Done when
      `ethos prove --full --json` on ETHOS's repository reports the decode gap before the fix and
      the same result as under a UTF-8 locale after it. (Before: one gap,
      `'gbk' codec can't decode     byte 0x92`; after: `full_proof_requires_execute`, as under
      `en_US.UTF-8`.)

## 2. Process text is UTF-8

- [x] 2.1 Make `run_command` decode output and encode input as UTF-8 unless the caller declares the
      encoding its command writes, delete the locale branch of `_decoded`, spool text input as
      UTF-8, and name `encoding="utf-8"` on the 17 direct `subprocess` text calls. Done when 1.1 and
      the process-adapter tests pass.
- [x] 2.2 Make the Windows PowerShell trust-anchor observation and process listing set
      `[Console]::OutputEncoding` to UTF-8 without a byte-order mark first. Done when their command
      tests pass with the statement; the release run's Windows jobs execute it.

## 3. One interpreter-flag owner

- [x] 3.1 Add the module that names `-B -I -X utf8`, and route every product and tool site that
      starts ETHOS's Python, and both console launchers, through it. Done when no product or tool
      file spells `"-B", "-I"` outside that module and the affected tests pass. (20 product and 18
      tool sites.)
- [x] 3.2 Add `-X utf8` to the npm launcher. Done when its launcher test passes.
- [x] 3.3 Assert that a Python started with the flags reports isolation and UTF-8 mode. Done when
      the probe reports `1 0` without `-X utf8` under a GBK locale and the test passes with it.

## 4. Explicit UTF-8 in ETHOS's own text I/O

- [x] 4.1 Name `encoding="utf-8"` at the sites Ruff's `PLW1514` reports and at the product and tool
      sites a syntax-tree scan of `read_text`, `write_text` and `open` finds, and resolve the
      `path-constructor-current-directory` preview finding. Done when Ruff passes under 4.2 and the
      scan finds no product or tool site. (24 product and tool sites, 31 test sites.)
- [x] 4.2 Select `PLW1514` with `preview = true` and `explicit-preview-rules = true` in
      `.config/checks/ruff/ruff.toml`. Done when the lint gate passes and an implicit read in a
      fixture fails it.
- [x] 4.3 Measure the dynamic guard. Done when the test calls without an encoding are counted and
      design.md names the guard's owner and condition. (1,321; the verification rebuild.)

## 5. Documentation and verification

- [x] 5.1 Record the change in `CHANGELOG.md` under Unreleased. Done when the prose and docs gates
      pass.
- [x] 5.2 Run every test module that imports a changed module. Done when they pass. (258 modules;
      the 95 failures were argv and encoding expectations, now updated, and the 28 files that held
      them pass: 681 tests.)
- [x] 5.3 Measure the product source budget. Done when the Python product total is at most 70,000
      effective lines and every touched file is within 500. (69,993; largest touched files 500.)
