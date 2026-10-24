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
- **Extract the installed common verification model at the existing CUE owner.** The product supplies version-matched model definitions and locked native compiler bytes; the repository supplies a real tracked CUE instance and typed native inputs. Product resources never masquerade as repository SourceTree members. Preview, drift check, exact-patch admission and provenance share one renderer, while ETHOS source-build jobs and genuine business increments remain local. Copying `tools.ci`, exposing an ETHOS checkout, and replacing the accepted CUE contract with Python/TOML generation were rejected: they respectively preserve the duplication, require developer source, or change accepted meaning. Installed and actual-adopter acceptance precede retirement; hosted claims remain open.
- **Compose runner preparation, locked supply checks and evidence through typed parameters.** The common model orders each declared GitLab runner's preparation before locked installation, shared native supply checks after installation, and proof last. Runner variables cannot replace the full-history requirement; additional evidence paths cannot remove the required verification report. Native compiler tests bind the actual DDWG Linux bootstrap, Windows PATH preparation, runner tags and time bounds. Shared Windows directory preparation is one native command, not a pipeline requiring retained glue. Arbitrary overrides of generated steps were rejected because they can replace verification; hardcoded adopter commands were rejected because acquisition and retained OS glue remain repository-owned. GitLab binds an existing offline-candidate variable name: only protected accepted/release API/web requests admit candidate offline pipelines, and source jobs exclude them. Retained offline jobs remain additive CUE jobs with independent deadlines; GitHub retains its separate offline workflow. Mandatory adopter variable renaming and arbitrary workflow-rule replacement were rejected. Release/offline acquisition retains its existing owner and trust boundaries.
- **Carry only the link-observation delta.** The requirements were accepted when `proof-throughput` archived; restating them here would create a second authority. The exception is the link observation: the accepted scenario kept every unavailable response nonpassing, which the 503 decision above changed, so this Change modifies that requirement and records the strict diagnostic rule beside it.
- **Deliver source projection before offline archive replacement.** This increment generates one source workflow per provider, with fixed common jobs and additive repository job maps. It emits no offline job or release-dispatch shortcut. Retain the independent offline workflow and its supplied archive until the existing owner qualifies exact release-payload acquisition and execution; source jobs exclude explicit offline-candidate requests. Local generation, installed admission, hosted execution and cold peer-outage acceptance remain separate.
- **Close on the delivered scope.** On 2026-10-24 [DR-0016](../../../docs/decisions/dr-0016-change-closure-scope.md) withdrew the tasks that this Change did not deliver from 0.2.0. Each withdrawn task keeps its line in `tasks.md` without a checkbox and returns through a new Change; the goals above describe the original scope.

## Risks / Trade-offs

- [An accepted requirement is specified before its implementation task closes] → The open task in this Change names the remaining work, and proof of this Change cannot pass until its tasks are complete.
- [A lane still edits `proof-throughput`] → That lane moves its edits to the successor named here when it next refreshes onto dev.
