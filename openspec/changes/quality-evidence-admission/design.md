# Design

## Context

The decisions behind these tasks are recorded in the archived design of `proof-throughput` (`openspec/changes/archive/2026-10-17-proof-throughput/design.md`). This Change keeps only the decisions needed to finish them.

## Goals / Non-Goals

**Goals:**

- Finish tasks 8.9, 8.10, 8.11, 8.12, 8.13, 10.4, 10.6, 10.7, 10.11, 10.12, 10.13, 11.9 against their original acceptance conditions.

**Non-Goals:**

- Weakening an acceptance condition, completing a task by archiving it, or adding obligations outside this outcome.

## Decisions

- **Move tasks verbatim with their original identities.** Renumbering was rejected, because commits, Attestations and peer threads already cite these identities.
- **Carry no requirement delta.** The requirements were accepted when `proof-throughput` archived; restating them here would create a second authority.

### Installed Document Quality

Tasks 11.9.2.1 and 8.13 reuse the existing product gate executor and native
tool declarations. Prettier and markdownlint-cli2 belong to the production
npm closure when offered to installed adopters; their original native policies
ship with that closure. Vale already has a shipped native executable and policy.
Source Markdown Nox consumes the same check owner rather than an alternate
implementation. The native Vale provider ships as a directly reusable capability;
source-wide activation requires current-corpus acceptance and does not replace
an adopter's already enforced Vale floor with Codespell. The incumbent source
spelling gate stays unchanged until that migration is qualified.

Checks select exact delivered Markdown, preserve immutable records and native
OpenSpec artifact ownership, reject empty or changed inputs, and retain native
diagnostics. Prettier owns layout; markdownlint owns compatible non-layout rules.
Candidate or ambient configuration cannot replace that common floor.

A subordinate Work Lane formatter previews native Prettier output, obtains
current exact-path prewrite admission, and applies only the same unchanged
preimages. It preserves index and Git refs, reports partial effects explicitly,
and never writes during proof. Refusal, repeat application, cancellation, native
lock closure, packaged execution and actual DDWG consumption qualify the result;
declarations or private package paths alone do not.

## Risks / Trade-offs

- [An accepted requirement is specified before its implementation task closes] → The open task in this Change names the remaining work, and proof of this Change cannot pass until its tasks are complete.
- [A lane still edits `proof-throughput`] → That lane moves its edits to the successor named here when it next refreshes onto dev.
