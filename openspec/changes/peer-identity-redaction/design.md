# Design

## Context

The archived `rc-plan` (Appendix F, from `peer-identity-records-draft5.md` with its decision and
amendment, reviewed by an independent reviewer, AIGW and fbee0c) settles the grammar, the span, the
feed, the verifier and the verb. This Change implements the parts adopters need to clear their
current trees: the grammar, the feed, `record_roots` and the verb. Labels only: H1 host, P1 and P2
ports, F1 namespace path, I1 project ID.

## Goals / Non-Goals

Goals:

- One grammar every later reader imports: the push check, the keyless verifier and
  `history-rebuild-map`.
- A verb that redacts the effective roots with a key the owner holds, previews without one, and
  proves its own output against the pre-redaction revision.

Non-Goals:

- `peer_identity.mode`, the push-time check, the CI backstop, the keyless commit verifier and wib's
  `[artifacts]` repair, which are `peer-identity-push-check`'s.
- Key creation, Keychain access, immutability of record roots and history rewriting.

## Decisions

1. **Grammar (F.2, F.3).** `ethos.repository.paradigm.peer_identity` owns, as pure functions over
   text: the four disjoint kinds by neighbours and the declared port; the marker and its pre-image
   (`ethos.private-peer.v1`, kind, lowercased host, port, normalized path, joined by NUL; scheme and
   userinfo never hashed); the key reader (64 lowercase hex, at most one trailing newline, never all
   zero: `redaction_key_invalid`); numeric replacement in 100000000 to 999999999 for I1 and 1024 to
   65535 for a port, probing a counter until the value differs from the original, every other
   replacement and every fed value and is absent from the domain, refusing after 4,096 probes
   (`numeric_replacement_exhausted`); the closed contexts; the boundaries; and
   `replacement_spans(line, feed)`, which returns the spans to replace and the `manual` occurrences
   that block an apply.
2. **Feed (F.4).** `ethos.adapters.repo.peer_feed` reads, for each release peer's `git_remote`,
   `git remote get-url --all` and `--push`, `remote.<name>.forgeRepository`, the multi-valued
   `forgeProjectId` and `forgeFormer` (`host=`, `path=`, `port=`), and the boolean `forgePrivate`. A
   peer is protected when its host is private-class or `forgePrivate` is true. Values never leave
   the process: results carry counts, forms and positions only.
3. **Record roots.** `RepositoryProfileDeclaration.record_roots` is a tuple of repository
   directories, each written with a trailing `/` as `immutable_roots` are, so a root matches whole
   segments only; a path without it, such as a file, is `repository_profile_invalid`. The effective
   roots are `immutable_roots` plus `record_roots`, with no added immutability;
   `effective_record_roots` in `ethos.repository.profile` owns them, so the commit verifier that
   `peer-identity-push-check` adds reads them without importing the verb.
4. **Verb.** `ethos lane redact private-addresses`, a lane maintainer verb beside `lane format`
   (`surface/cli/lane/redaction.py`, owner `application/redaction.py`):
   - The default preview needs no key. It reads the tracked tree at the lane head and lists, per
     occurrence, its file, line, form (`url`, `scp`, `authority`, `host`, `path`, `id`, `port`,
     `manual`) and whether it lies in the effective roots, plus the count outside them; no value.
   - `--apply --key-stdin --authorize --expect-head <oid>` admits each file it writes through the
     lane's exact-path prewrite and the Lease, under a compare of the lane head, and writes markers
     and numbers in the effective roots of the working tree only. An unfed path after a replaced
     host is `manual` and blocks the apply.
   - `--verify --key-stdin --base <rev> --head <rev>` re-derives every marker and number of `head`
     from `base` and, on a pass, records the Attestation `redaction:private-peer` with base, head,
     roots, count and the key generation `hex(HMAC(key, "ethos.redaction.generation.v1"))[:16]`, as
     proof evidence is recorded, where the count is the occurrences in the roots at the base;
     without the base it is `unknown`.
   - A file whose SHA-256 a record in the same commit holds gets that digest rewritten (digest
     follow). A key of another generation than the last recorded one refuses
     (`redaction_key_generation_changed`) unless `--rotate` is given.
5. **Spans, as implemented (F.3).** After a fed host of kind `url`, `authority` or `host`, the span
   takes an optional `:port` and then the longest fed path, current or former, that the following
   whole segments start with, case-insensitively, plus a trailing `.git` when the path ends at the
   last segment; the remaining segments stay outside the span. Segments after a fed host that start
   no fed path make the occurrence `manual`, so no unfed path survives behind a marker. For `scp`
   the host alone is the span and the fed path after the colon a standalone `path` span; an unfed
   path there is `manual` too. A fed path elsewhere in a line is a standalone `path` span when its
   boundaries hold; a single-segment namespace never counts alone.
6. **Markers in the content scans.** The private-class pattern never matches the marker, a
   `.invalid` host; the bracket form `[redacted:private-network-address:hmac-sha256:<hex>]`, which
   no tracked record uses, retires from the specification and the test pins.

## Risks / Trade-offs

- A rotated key forgoes verification of earlier generations unless their key is kept.
- Another spelling of H1 or a port in free prose is not found; the preview's count is the stated
  bound, as the archived design records.
- Size: about +600 product and +350 test effective lines; tests share one fixture repository and
  vector tables, since the test budget had 3,022 lines left on 2026-11-08.
