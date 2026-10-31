# Design

## Context

`run_command` in `src/ethos/adapters/process.py` is the one adapter for external argv commands. It
defaults to text mode, and `_decoded` decodes captured output with `locale.getencoding()` unless the
process runs in UTF-8 mode or the caller passes `output_encoding`. Text standard input is spooled
through a `TemporaryFile(mode="w+")`, which also uses the locale. Only the two dumper calls in
`src/ethos/adapters/gates/tool.py` pass an encoding. The Git adapter runs Git with `LC_ALL=C` and
text mode, so Git's UTF-8 commit messages, paths and configuration values are decoded with the
locale.

Every Python process that ETHOS starts runs with `-B -I`: the CLI's re-exec into the selected
runtime (`src/ethos/cli.py`), `runtime_command` (`src/ethos/adapters/repo/runtime/selection.py`),
the hook next actions and admission runner, proof admission, runtime post-observation, the
materialization probes, uv through supply Python, the release console launchers rendered in
`src/ethos/adapters/repo/runtime/materialization/python_image.py`, and about a dozen prefixes in
`tools/ci/`. Twelve product sites spell the flags themselves, and one hook next action spells only
`-I`. `-I` implies `-E`, so `PYTHONUTF8` and `PYTHONIOENCODING` have no effect; only `-X utf8` turns
on UTF-8 mode.

Ruff 0.17.3 implements `unspecified-encoding` (`PLW1514`) as a preview rule. On `dev` at `4edfa8f43`
it finds 4 product sites, 1 tool site and 31 test sites. With `preview = true` and
`explicit-preview-rules = true` the managed configuration gains one further finding,
`path-constructor-current-directory`, a preview extension of a stable rule. The pytest configuration
already declares `filterwarnings = ["error"]`, and the test gate starts pytest with
`python -m pytest`, without `-I`.

## Goals / Non-Goals

**Goals:**

- ETHOS behaves the same on every host locale: every byte it reads from or writes to a file or a
  process means the same text.
- One owner for how ETHOS starts its own Python, so a flag changes in one place.
- A regression fails before a release: statically for ETHOS's own I/O calls and dynamically for any
  implicit locale encoding that a test reaches.

**Non-Goals:**

- Changing the Git hook launcher or its generation digest.
- Changing how a governed repository's own scripts redirect output.
- Supporting a command that writes a non-UTF-8 encoding: none exists among ETHOS's commands today,
  and the declared-encoding parameter stays for one that would.

## Decisions

1. **Process text defaults to UTF-8, not the locale.** `run_command` decodes output and encodes
   input as UTF-8 unless the caller declares the encoding its command always writes, and `_decoded`
   no longer consults the locale or UTF-8 mode. Declaring UTF-8 at about 60 call sites was rejected:
   the same declaration everywhere is the default, and a new call site would again inherit the
   locale. Mirroring Python's text-mode pipe was the old intent, but the commands ETHOS runs write
   UTF-8 whatever the host locale: Git, Go, Node, Mise, uv, Ruff, ty, Taplo, CUE and Gitleaks do so
   natively, ETHOS's Python children do so through Decision 2, and the two Windows PowerShell
   commands (the trust-anchor observation and the process listing) set `[Console]::OutputEncoding`
   to UTF-8 without a byte-order mark as their first statement.
2. **One interpreter-flag owner, `-B -I -X utf8`.** A small module in
   `src/ethos/adapters/repo/runtime/` owns the flags and builds `python <flags> -m ethos.cli ...`,
   `python <flags> -m uv ...` and `python <flags> -c ...`; every product and tool site, and both
   console launchers, use it. UTF-8 mode makes the default encoding of `open`, the standard streams
   and child pipes UTF-8 for ETHOS and every library it loads, which is the behaviour Python 3.15
   adopts. Relying on Decision 1 and explicit encodings alone was rejected: a third-party library's
   implicit read, a probe's printed path and human output redirected to a file would still follow
   the locale. Setting `PYTHONUTF8` was rejected because `-I` ignores it.
3. **Static and dynamic guards on ETHOS's own text I/O.** ETHOS's file reads and writes name
   `encoding="utf-8"`; Ruff's `PLW1514` enforces it as an explicitly selected preview rule in the
   managed configuration, the one owner of Ruff policy for ETHOS and every governed Python
   repository. The test gate sets `PYTHONWARNDEFAULTENCODING=1` in the environment, which pytest and
   its xdist workers inherit, so `EncodingWarning` reaches the existing
   `filterwarnings = ["error"]`. A product AST rule was rejected because Ruff already implements the
   check; a pytest-only guard was rejected because it sees only exercised paths.
4. **The hook launcher keeps `-B -I`.** Its text is part of the hook generation digest, and a change
   would mark every installed hook stale in every governed repository. Git starts the hook with
   ASCII arguments and reference lines; its semantic work starts ETHOS's runner and other commands
   through the boundaries above. A later Change that alters the hook contract for its own reason can
   add the flag.

## Risks / Trade-offs

- A governed Python repository with implicit encodings fails Ruff after upgrading. The managed
  policy meant this: the same defect blocks Windows hosts there, and Ruff's fix is mechanical.
- `preview = true` also enables preview behaviour of stable rules, and a Ruff upgrade can change it.
  Ruff is pinned, so an upgrade already passes the full proof.
- A command that writes invalid UTF-8 now fails the decode on every host, not only on some. That
  failure is the existing typed process gap.
- The product source budget had 22 effective lines of headroom after alpha.24. One flag owner
  replaces about 25 spelled prefixes, which is expected to reduce product lines.
