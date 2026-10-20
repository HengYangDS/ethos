# Design

## Context

The decisions behind these tasks are recorded in the archived design of `proof-throughput` (`openspec/changes/archive/2026-10-17-proof-throughput/design.md`); those behind 3.8 are in the archived design of `repository-paradigm`. This Change keeps only the decisions needed to finish them.

## Goals / Non-Goals

**Goals:**

- Finish tasks 3.8, 7.3, 7.4, 7.5, 7.9, 7.11, 7.12, 7.13 against their original acceptance conditions.

**Non-Goals:**

- Weakening an acceptance condition, completing a task by archiving it, or adding obligations outside this outcome.

## Decisions

- **Move tasks verbatim with their original identities.** Renumbering was rejected, because commits, Attestations and peer threads already cite these identities.
- **Pace `github.com` and accept 503 in the shared link configuration.** GitHub answers bursts of unauthenticated page requests with 429, and an occasional request with 503 even at a low rate, on GitLab's intranet egress and on GitHub-hosted runners alike, so a different link fails in each run. The lychee configuration checks `github.com` links two at a time, 250 ms apart, and retries a 429 or a timeout. Lychee never retries a rejected 503, and a 503 reports temporary unavailability rather than a broken link, so 503 is accepted alongside the default success codes. Checking through the GitHub API with a token was rejected: GitLab holds no GitHub credential, and the observation should mean the same on both providers.
- **Keep the link gate strict about Lychee diagnostics.** The gate fails when Lychee writes anything to stderr, including its hint about followed redirects, so documents link to the resolved target of a redirect. Ignoring Lychee's hints was rejected: a redirect is drift the document owner can fix, and ignoring hints would also hide a new diagnostic.
- **Carry no requirement delta.** The requirements were accepted when `proof-throughput` archived; restating them here would create a second authority.

## Risks / Trade-offs

- [An accepted requirement is specified before its implementation task closes] → The open task in this Change names the remaining work, and proof of this Change cannot pass until its tasks are complete.
- [A lane still edits `proof-throughput`] → That lane moves its edits to the successor named here when it next refreshes onto dev.
