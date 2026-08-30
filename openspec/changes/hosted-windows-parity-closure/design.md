## Context

The hosted adopter fixture writes both LF and CRLF byte sequences and compares
the staged Git blobs with those bytes. On Windows, Git commonly enables
`core.autocrlf`; without a repository-local attribute, `git add` normalizes the
CRLF fixture to LF. That is host configuration leakage, not a product storage
failure.

Separately, hosted quality runs the repository-hygiene owner while the canonical
full proof omits it. Four tracked test suppressions therefore passed local
proof and failed only after publication.

## Goals / Non-Goals

**Goals:**

- Make the same line-ending assertion mean the same thing on every host.
- Make the canonical full proof execute repository hygiene before publication.
- Remove the existing suppressions rather than exempting them.

**Non-Goals:**

- No Windows-only expected values or `core.autocrlf` mutation.
- No hygiene allowlist, baseline, negative exception, or hosted retry.
- No redesign of package delivery or unrelated quality gates.

## Decisions

The generated adopter repository owns its test-file byte semantics through a
tracked `.gitattributes` entry marking only the line-ending fixtures as binary.
This leaves ordinary adopter text policy untouched while making the byte
round-trip invariant independent of host defaults.

Repository hygiene becomes one declared offline gate in `system/gates.toml` and
one member of the full proof set. Existing tests use typed casts at their fake
framework boundaries, so no suppression remains to hide from that gate.

## Risks / Trade-offs

- The full proof gains one fast repository scan that hosted CI already treats
  as mandatory.
- The fixture deliberately tests byte preservation, not Git text
  normalization; `.gitattributes` makes that distinction explicit.
