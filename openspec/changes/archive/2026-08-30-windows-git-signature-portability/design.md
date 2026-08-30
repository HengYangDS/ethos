## Context

The Git-object adapter already owns SSH signature verification and the package
smoke already owns installed publication-plan validation. The hosted failure is
caused by one line-ending assumption at the first owner; the second owner hides
that typed result behind a generic exception.

## Goals / Non-Goals

**Goals:**

- Make the existing trust parser accept the two line endings emitted by
  supported Git hosts without weakening the trusted status grammar.
- Keep the original publication gaps visible at the package-smoke boundary.

**Non-Goals:**

- No global output normalization, Windows-specific branch, retry, fallback, or
  alternate trust verifier.
- No redesign of publication, package installation, or unrelated hosted gates.

## Decisions

The existing anchored regular expression will admit an optional carriage return
immediately before each line boundary. This changes only the representation of
the same terminal Git status; it does not strip arbitrary whitespace or accept
partial output.

The smoke failure will format the already-returned `required_gaps` together
with the command identity. No diagnostic framework or parallel result schema is
introduced.

## Risks / Trade-offs

- A broader normalization could accidentally accept malformed output; the
  repair is therefore restricted to `\r?` at the terminal line boundary.
- Exception text is not repository authority, but preserving the typed gaps
  makes hosted logs sufficient to identify the owning failure without replay.
