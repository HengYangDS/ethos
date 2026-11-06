# Design

## Context

See [proposal.md](proposal.md). `tarfile.TarFile.extractfile` is typed to return `IO[bytes]`, and
`hashlib.file_digest` accepts only a buffered binary file or a `BytesIO`-like object.

## Goals / Non-Goals

Goals:

- The type gate passes without an ignore comment.

Non-goals:

- Changing what is hashed or how a member is selected.

## Decisions

- **Read in chunks.** One-mebibyte reads into `hashlib.sha256` keep memory bounded for the
  150-megabyte executable and need no cast.

## Risks / Trade-offs

- None beyond the existing archive-reading test, which pins the digest of a known member.
