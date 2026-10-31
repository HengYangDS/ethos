# Proposal

## Why

The 0.2.0-alpha.24 release blocks every proof on a Windows host whose code page is not UTF-8. On the
data-department-work-guidelines GitLab Windows ARM64 runner, whose code page is 936,
`ethos prove --host --execute --full --json` stopped after about 4 seconds with the required gap
`'gbk' codec can't decode byte 0x94 in position 38: illegal multibyte sequence` (pipeline 13536, job
62963). 0x94 is the last byte of the UTF-8 em dash. On macOS the same failure follows from
`LC_ALL=zh_CN.GBK`: `ethos prove --full --json` on ETHOS's own repository reports one gap,
`'gbk' codec can't decode byte 0x92`.

The shared process adapter decodes every command's text output with the host locale unless the
caller names an encoding (`src/ethos/adapters/process.py`, `_decoded`). About 60 product callers use
text mode and two name an encoding. Git, Go, Node, Mise, uv, Ruff and ty write UTF-8, so a code page
936 host fails the decode and a code page 1252 host decodes the same bytes into wrong text without
an error. The adapter also encodes the text it writes to a command's standard input with the locale.
Twenty-four product and tool reads and writes of ETHOS's own files name no encoding. Every Python
process that ETHOS starts runs with `-B -I`, which ignores `PYTHONUTF8`, so it also reads, writes
and prints with the locale. Python 3.15 makes UTF-8 mode the default (PEP 686); ETHOS supports
Python 3.12 to 3.14.

## What Changes

- Process text is UTF-8. The shared process adapter decodes output and encodes input as UTF-8 unless
  the caller declares the encoding that its command always writes. The host locale no longer selects
  it. The two Windows PowerShell commands set their output encoding to UTF-8 first.
- ETHOS's Python processes run in UTF-8 mode. One product module names the interpreter flags
  `-B -I -X utf8`, and every Python process that ETHOS starts uses them: the selected-runtime
  re-exec, runtime commands, hook next actions and the admission runner, proof admission, runtime
  post-observation, materialization probes, uv through supply Python, the gates that run Ruff, uv
  and codespell, the release console launchers and the release tooling. The npm launcher adds
  `-X utf8` to its `-P`.
- ETHOS reads and writes its own text files as UTF-8 by name. Ruff's `unspecified-encoding`
  (`PLW1514`) joins the managed lint policy as an explicitly selected preview rule.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `adapters`: process text is UTF-8 unless a command declares another encoding.
- `runtime-activation`: the internal execution authority and uv through supply Python run in UTF-8
  mode.
- `repository-governance`: the Work Lane runner bootstrap runs in UTF-8 mode.

## Impact

- `src/ethos/adapters/process.py`, `src/ethos/adapters/repo/trust_anchor/filesystem.py` and the new
  `src/ethos/adapters/repo/runtime/interpreter.py`, with the 20 product and 18 tool sites that start
  ETHOS's Python, and `distributions/npm/bin/ethos.mjs`.
- `.config/checks/ruff/ruff.toml`, which the package ships: governed Python repositories receive
  `PLW1514` when they upgrade (on 11-01: filmkit 8 sites, openai-responses-proxy 5,
  ethos-introduction-film 1).
- Out of scope: the Git hook launcher keeps `-B -I`, so its generation digest and every installed
  hook stay current; its work runs through the UTF-8 process and file boundaries above. A governed
  repository whose own CI redirects JSON through Windows PowerShell 5.1 `>` still receives UTF-16;
  that redirection is the repository's script.
