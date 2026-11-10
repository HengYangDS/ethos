# Design

## Context

See the [proposal](proposal.md). ETHOS's layers import downward; the kernel (`ethos.contracts`,
`ethos.normalization`) is importable from every layer and from `tools/`.

## Goals / Non-Goals

Goals:

- One owner per behavior, in the lowest module every caller may import.
- A gate that refuses a second copy as soon as it is written.

Non-Goals:

- The 34 identical bodies in `tests/`; they move with the single fixture authority.
- Changing any refusal's gap, verdict or message.

## Decisions

1. Identity is structural: a body is compared after renaming what it binds, in order of first use
   across the signature and the body, keeping every name it reads. `a - b` and `b - a` differ;
   a renamed copy does not.
2. Below 4 statement and expression nodes (the module wrapper and Load/Store markers not counted)
   a body is an idiom such as `return name`; a delegated call such as `raise ValueError(reason)` is
   the smallest implementation. What a body binds includes parameters, targets, `except ... as`,
   `match` captures, nested definitions and imports. There is no allowlist.
3. A script run by `uv run --no-project python ...` in a workflow is its own deployment unit; it
   cannot import an owner. The gate reads that set from `.github/workflows/`, skips it, and
   requires it to import only `sys.stdlib_module_names`. `tools/ci/delivery/release_assets.py` keeps
   its own standard-library digest.
4. `refuse(*gaps, cause=None)` raises `refusal(*gaps)`, chained `from cause` only when a cause is
   given; otherwise the error being handled stays the implicit context, as a plain raise keeps it.
   Call sites keep a statement, because Ruff's message rule refuses a string literal inside
   `raise`. The four functions that end in a refusal raise it explicitly, so the implicit-return
   rule sees the exit.
5. `file_sha256` reads in bounded chunks with `hashlib.file_digest`; callers and their tests keep
   the name `file_sha256`.
6. The two identical model digest methods become one function, `model_digest(model)`, found
   through the type checker: removing the methods named exactly the nine call sites.

## Risks / Trade-offs

- A caller that records a plain `ValueError` as a cause now sees an `OutcomeError` and keeps its
  class code. The impacted sweep names any test whose expectation depended on that.
- `ethos.contracts.digest` now reads files. It stays standard-library only and read-only.
- Ten former aliases raised `from cause` with a default of `None`, which hid the error being
  handled. They now keep it as the context, so a failure chain such as the native tool supply's
  can name one more earlier error.
