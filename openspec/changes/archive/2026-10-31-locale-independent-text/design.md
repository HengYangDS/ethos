# Design

## Context

`run_command` in `src/ethos/adapters/process.py` is the one adapter for external argv commands. It
defaults to text mode, and `_decoded` decodes captured output with `locale.getencoding()` unless the
process runs in UTF-8 mode or the caller passes `output_encoding`. Text standard input is spooled
through a `TemporaryFile(mode="w+")`, which also uses the locale. Only the two dumper calls in
`src/ethos/adapters/gates/tool.py` pass an encoding. The Git adapter runs Git with `LC_ALL=C` and
text mode, so Git's UTF-8 commit messages, paths and configuration values are decoded with the
locale. Nine product and eight tool calls start a command through `subprocess` directly, in text
mode without an encoding, so they decode with the locale too. ETHOS also runs Windows PowerShell
twice, for the trust-anchor observation and the process listing; redirected, it writes in the
console code page.

Every Python process that ETHOS starts runs with `-B -I`: the CLI's re-exec into the selected
runtime (`src/ethos/cli.py`), `runtime_command` (`src/ethos/adapters/repo/runtime/selection.py`),
the hook next actions and admission runner, proof admission, runtime post-observation, the
materialization probes, uv through supply Python, the gates that run Ruff, uv and codespell, the
release console launchers rendered in
`src/ethos/adapters/repo/runtime/materialization/python_image.py`, and the release tooling in
`tools/ci/`. Twenty product sites and eighteen tool sites spelled the flags themselves, one hook
next action spelled only `-I`. `-I` implies `-E`, so `PYTHONUTF8` and `PYTHONIOENCODING` have no
effect; only `-X utf8` turns on UTF-8 mode.

Ruff 0.17.3 implements `unspecified-encoding` (`PLW1514`) as a preview rule. On `dev` at `6813ec3e4`
it finds 4 product sites, 1 tool site and 31 test sites; a syntax-tree scan of `read_text`,
`write_text` and `open` calls finds 19 more product and tool sites, on expressions whose type Ruff
does not infer, such as `(root / MISE_CONFIG).read_text()`. With `preview = true` and
`explicit-preview-rules = true` the managed configuration gains one further finding,
`path-constructor-current-directory`, a preview extension of a stable rule.

## Goals / Non-Goals

**Goals:**

- ETHOS behaves the same on every host locale: every byte it reads from or writes to a file or a
  process means the same text.
- One owner for the flags ETHOS starts its own Python with, so a flag changes in one place.
- A regression of ETHOS's own text I/O fails lint before a release.

**Non-Goals:**

- Changing the Git hook launcher or its generation digest.
- Changing how a governed repository's own scripts redirect output, or the encoding with which
  ETHOS's gates run a governed repository's tests.
- Supporting a command that writes a non-UTF-8 encoding: none exists among ETHOS's commands today,
  and the declared-encoding parameter stays for one that would.

## Decisions

1. **Process text defaults to UTF-8, not the locale.** `run_command` decodes output and encodes
   input as UTF-8 unless the caller declares the encoding its command always writes, and `_decoded`
   no longer consults the locale or UTF-8 mode; the direct `subprocess` calls replace `text=True`
   with `encoding="utf-8"`. Declaring UTF-8 at about 60 call sites was rejected: the same
   declaration everywhere is the default, and a new call site would again inherit the locale.
   Mirroring Python's text-mode pipe was the old intent, but the commands ETHOS runs write UTF-8
   whatever the host locale: Git, Go, Node, Mise, uv, Ruff, ty, Taplo, CUE and Gitleaks do so
   natively, ETHOS's Python children do so through Decision 2, and the two Windows PowerShell
   commands set `[Console]::OutputEncoding` to UTF-8 without a byte-order mark as their first
   statement. A host without a console keeps its code page; the statement does not fail there.
2. **One interpreter-flag owner, `-B -I -X utf8`.** `src/ethos/adapters/repo/runtime/interpreter.py`
   names the flags, and every product and tool site that starts ETHOS's Python, and both console
   launchers, use them. UTF-8 mode makes the default encoding of `open`, the standard streams and
   child pipes UTF-8 for ETHOS and every library it loads, which is the behaviour Python 3.15
   adopts. Relying on Decision 1 and explicit encodings alone was rejected: a third-party library's
   implicit read, a probe's printed path and human output redirected to a file would still follow
   the locale. Setting `PYTHONUTF8` was rejected because `-I` ignores it. A command builder beside
   the flags was rejected: the flags are the decision, and the call sites keep their own arguments.
3. **Explicit UTF-8 in ETHOS's own text I/O, guarded statically.** Every product and tool read and
   write of a text file names `encoding="utf-8"`, and the syntax-tree scan above finds none left.
   Ruff's `PLW1514` enforces the cases Ruff can type, as an explicitly selected preview rule in the
   managed configuration, the one owner of Ruff policy for ETHOS and every governed Python
   repository. A dynamic guard was measured and deferred: with `PYTHONWARNDEFAULTENCODING=1` the
   test gate's `-W error` stops at collection, because the tests make 1,321 text calls without an
   encoding, and naming it at each would exceed the 90,000-line test budget. The verification
   rebuild owns writing test text through UTF-8 fixtures and then arming the warning. A product
   syntax-tree rule was rejected because Ruff owns the check.
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
- The Windows PowerShell statement is verified by the Windows hosted tests and the adopter Windows
  acceptance, not on this macOS host.
- Until the dynamic guard is armed, a test-only implicit encoding can still pass on a UTF-8 host;
  ETHOS's own processes run in UTF-8 mode either way.
