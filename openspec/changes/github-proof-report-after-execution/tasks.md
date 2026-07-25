## 1. Diagnosis and authority

- [x] 1.1 Bind GitHub dev run `30172606031` to exact commit
  `b2e474590234622fde1631a4ddb514fef6386a9f`.
- [x] 1.2 Preserve the retained audit, report, proof, JUnit, and coverage
  artifacts showing a green 21-gate proof combined with a stale pre-proof report.
- [x] 1.3 Confirm the defect is deterministic producer order rather than a test,
  timeout, worker, or retry failure.
- [x] 1.4 Continue in the ETHOS-owned Work Lane bound to Claim
  `github-proof-report-after-execution-20260725`.
- [x] 1.5 Keep GitLab mutation and observation frozen.

## 2. Contract and implementation

- [x] 2.1 Add a behavioral contract requiring report to observe the proof attempt
  from the same owner-script execution; observe the expected RED failure.
- [x] 2.2 Move only the report invocation after the proof attempt.
- [x] 2.3 Observe focused GREEN and run the complete provider projection test
  module.
- [x] 2.4 Pass shell lint, quality audit, strict OpenSpec, Claim, and changed-scope
  checks.

## 3. Proof and closeout

- [ ] 3.1 Refresh generic parity evidence after overlapping foreign activity is
  clear and require zero parity gaps.
- [ ] 3.2 Run exact-HEAD `ethos prove --execute` and require every gate to pass.
- [ ] 3.3 Complete only evidence-backed active tasks and validate the carrier for
  official archive.

## Post-archive transition boundary

Official archive, archive-HEAD parity and proof, current-base refresh if
necessary, candidate land, accepted-root closeout, repo-family closeout, and
owned-Lane retirement are lifecycle transitions rather than unfinished active
Change tasks.

After accepted local closeout, publish GitHub `dev` and wait for the exact SHA.
Publish `main` only after dev is green, then observe exact main ETHOS CI and
CodeQL outcomes. Do not rerun the deterministic failed predecessor job. GitLab
remains outside the transition set while intranet access is unavailable.

Create the immutable metadata-only closeout record only after local and GitHub
transitions have current evidence. Preserve `CURRENT`, refresh the records index,
and remove only task-owned temporary files.
