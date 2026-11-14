---
subject: ethos:foundations-hosted-ci
role: research
state: active
relations:
  part_of: ../modern-engineering-foundations.md
  informs: ../../plans/terminal-governance-product-design.md
  constrained_by: ../../governance/product-design-contract.md
---

# Hosted CI Practice

This page records the hosted CI evidence that the archived `common-base-plan` design cites as
packet N, where N is an item of the checklist below.

Research date 2026-11-13. "Undated" means a live page without a revision date. Sources are primary
(GitHub Docs and changelog, GitLab Docs, SLSA, OpenSSF, Sigstore, mise, uv, PyPI) except where
marked unofficial. Items 25 and 27 are inferences.

## Checklist

Security

1. Commit `actions.lock` (`gh actions-lock`); enforce the Require-lockfile or SHA-pinning policy.
   Tags move; the lock covers transitive actions.
   <https://github.blog/changelog/2026-10-28-github-actions-workflow-lockfiles-are-generally-available/>
   (GA 2026-10-28).
2. Top-level `permissions: contents: read`, widened per job; OIDC instead of stored secrets.
   <https://docs.github.com/en/actions/reference/security/secure-use> (undated).
3. Build job without `id-token`; publish job with it behind an environment;
   `persist-credentials: false`; no caches in release jobs.
   <https://docs.astral.sh/uv/guides/integration/github/> (2026-11-03).
4. Avoid `pull_request_target`; never check out fork code. Blocked by default in public repositories
   from 2026-12-02; checkout v7 refuses fork checkouts.
   <https://github.blog/changelog/2026-11-02-pull_request_target-blocked-by-default-december-2/>
   (2026-11-02).
5. Release environment: required reviewers, prevent self-review, tag-only refs, no admin bypass.
   <https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments>
   (undated).
6. `actions/attest@v4`; consumers run `gh attestation verify`; an isolated reusable build workflow
   for SLSA Build L3; attestation alone is L2; private repositories need Enterprise Cloud.
   <https://docs.github.com/en/actions/concepts/security/artifact-attestations> (undated).
7. Immutable releases lock tags and assets and add a Sigstore release attestation.
   <https://github.blog/changelog/2025-10-28-immutable-releases-are-now-generally-available/>
   (GA 2025-10-28).
8. PyPI Trusted Publishing with PEP 740 attestations on both forges.
   <https://docs.pypi.org/attestations/producing-attestations/> (undated).
9. OpenSSF Scorecard: read-only top-level token, hash pins, no dangerous triggers; in-toto release
   provenance files score 10/10.
   <https://github.com/ossf/scorecard/blob/main/docs/checks.md> (main, undated; mostly GitHub-only).
10. GitLab: protected variables on protected refs only, masked-and-hidden variables;
    pipeline-variable override role `no_one_allowed`; inputs over variables; masking is no
    boundary. <https://docs.gitlab.com/ci/variables/> (17.6; Masked default 18.3).
11. GitLab job-token allowlist minimal, admin-enforced, never disabled.
    <https://docs.gitlab.com/ci/jobs/ci_job_token/> (17.x to 19.x).
12. GitLab runners: the Parallels executor is the "safest possible option" with
    `disable_snapshots = true` (VMs destroyed after jobs; distributed cache only); no shell or
    privileged Docker; protected runners for release; segmented network; reused hosts persist
    compromise. <https://docs.gitlab.com/runner/security/> (undated).
13. GitLab keyless cosign (`id_tokens`, aud `sigstore`) is GitLab.com-only; Self-Managed needs its
    own Sigstore. <https://docs.gitlab.com/ci/yaml/signing_examples/> (undated).

Speed

14. `concurrency` group `${{ github.workflow }}-${{ github.ref }}`, pull-request-only
    `cancel-in-progress` expression; `queue: max` for releases.
    <https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency>
    (queue 2026-05-07).
15. GitLab auto-cancel with `on_new_commit: interruptible`, `interruptible: true` on tests (default
    false), `on_job_failure: all`. <https://docs.gitlab.com/ci/yaml/> (19.x).
16. Key caches on OS, architecture and lockfile; mise: cache checksum-verified downloads rather than
    installs, `mise install --locked`; uv: `uv.lock` key plus `uv cache prune --ci`; restored
    installs are not re-verified. <https://mise.jdx.dev/continuous-integration.html> (mise
    2026.10.4, mise-action v5).
17. Lint and type jobs first, then a `needs` fan-out; matrix at most 256 jobs, GitLab `parallel` at
    most 200, `needs` at most 50. <https://docs.github.com/en/actions/reference/limits> (undated).
18. Path-filtered workflows leave required checks pending: use one always-run gate job (`needs`,
    `if: always()`); GitLab's Pipelines-must-succeed blocks merge requests with no pipeline.
    <https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks>
    (undated).
19. A merge queue needs a `merge_group` trigger; GitLab merge trains are Premium+, 20 parallel by
    default. <https://docs.gitlab.com/ci/pipelines/merge_trains/> (enforcement GA 19.3).

Reliability

20. Retry infrastructure only: GitLab `retry:when` runner_system_failure, scheduler_failure,
    api_failure, or `exit_codes`; never the default `always`; retries mask flakes.
    <https://docs.gitlab.com/ci/yaml/> (reasons split 19.1).
21. Quarantine flaky tests: linked issue, exclusion tag, separate job.
    <https://docs.gitlab.com/development/testing_guide/quarantining_tests/> (undated).
22. Explicit `timeout-minutes`; hosted jobs die at 6 hours (limits page above).
23. macOS: 5 concurrent jobs on Free to Team plans; reports of `macos-latest` jobs cancelled after
    about 15-minute queues; run macOS in the queue or on main, track queue time.
    <https://github.com/orgs/community/discussions/212075> (2026-11-04, unofficial).
24. Windows on Arm: `windows-11-arm` (VS2026 image); CPython Tier 2; require uv 0.13.0 or later
    (native ARM64 Python default). <https://github.com/astral-sh/uv/issues/12906> (closed
    2026-10-16); <https://peps.python.org/pep-0011/> (2026-10-31).

Reuse

25. One source of truth: `mise run` tasks; thin YAML via reusable workflows or composite actions and
    GitLab components pinned to SHA (instance-local). <https://docs.gitlab.com/ci/components/> (GA
    17.0, 2024). Inference.

Measurement

26. Track queue time, p50 and p95, failure and re-run rates, minutes and DORA lead time: GitHub
    Performance Metrics plus REST jobs (`started_at` minus `created_at`, `run_attempt`); GitLab
    analytics plus the Jobs API `queued_duration`.
    <https://github.blog/changelog/2025-03-14-actions-performance-metrics-are-generally-available-and-enterprise-level-metrics-are-in-public-preview/>
    (2025-03-14); <https://dora.dev/guides/dora-metrics/> (2026-01-05).

Local-first parity

27. Local proof is not release evidence: SLSA Build L2 and above need a hosted builder signing
    provenance; record local results as in-toto test-result attestations.
    <https://slsa.dev/spec/v1.2/build-track-basics> (v1.2). Inference.
28. Shared caches: CI-only writers (`--remote_upload_local_results=false` for developers),
    reproducible builds; poisoning risk. <https://bazel.build/remote/caching> (undated).

## Changes In 2025 And 2026

- GitHub: SHA-pin and block policy (2025-08-15); immutable releases GA (2025-10-28); reusable
  workflows 10 nested, 50 calls (2025-11-06); `pull_request_target` runs the default-branch workflow
  and environment rules match `GITHUB_REF` (2025-12-08); hosted prices cut up to 39 percent
  (2026-01-01), self-hosted fee postponed; arm64 standard runners in private repositories
  (2026-01-29); `macos-26` GA (2026-02-26), now `macos-latest`; `queue: max` (2026-05-07); Node 24
  default 2026-06-16, Node 20 removed 2026-09-23; checkout fork guard backported to major tags
  2026-07-20, SHA pins excluded; `windows-11-arm` moved to VS2026 (2026-09-21 to 30); lockfiles GA
  (2026-10-28).
- GitLab: Masked default (18.3); 100 components per project (18.5); job performance analytics,
  limited availability (18.9); merge-train parallel limit (19.0); retry reasons split (19.1); train
  enforcement (19.3); `default: timeout` behind a disabled flag (19.6, likely unreleased).
- uv 0.13.0: native Windows ARM64 Python.

## Open Unknowns

- No official macOS queue-time data or SLA; measure your own.
- `windows-11-arm` GA is never stated; the docs list it unlabelled.
- The mise docs do not confirm a `windows-arm64` lock platform.
- Require-lockfile is reportedly missing from the REST API (user comment, 2026-11-11).
- Not stated: the GitLab allowlist-enforcement version, GitLab-native provenance signing status,
  macOS guests under Parallels.
- No first-party affected-test selection; no official guidance on generating both forges' YAML or
  on skipping hosted CI after a signed local proof.
