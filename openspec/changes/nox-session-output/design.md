# Design

## Context

See [proposal.md](proposal.md). `noxfile.py` registers the sessions that `tools/ci/sessions.py`
implements, and Nox configures logging before it loads them. Several ETHOS modules parse Markdown
with markdown-it, so any session that runs them in process prints its debug records.

## Goals / Non-Goals

**Goals:**

- A session's output is its own report and diagnostics.

**Non-Goals:**

- Changing Nox's own log level, which also controls the commands Nox prints.
- Changing logging in the product, which configures no root logger.

## Decisions

- **The session module sets markdown-it's logger to info.** `tools/ci/sessions.py` is the
  application module that every session is loaded from, so one statement there covers every
  session. Info keeps markdown-it's warnings and errors.

## Risks / Trade-offs

- [Another library logs at debug level inside a session] → It is handled the same way when it is
  observed; the root level stays as Nox sets it.
