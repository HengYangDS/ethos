## 1. Diagnosis and authority

- [x] 1.1 Bind GitHub main run `30163837735` to exact commit `80272b76c` and
  preserve the successful first full test step plus failed duplicate proof step.
- [x] 1.2 Confirm `ethos prove --execute` already includes the
  `unit-architecture` owner script in the default 21-gate graph.
- [x] 1.3 Compare removal, receipt reuse, and host-global serialization; select
  removal of the redundant direct step as the minimum trust-preserving change.
- [x] 1.4 Create the owned ETHOS Work Lane and bind it to Claim
  `github-single-head-bound-proof-20260725`.
- [x] 1.5 Keep GitLab mutation and observation frozen.

## 2. Contract and implementation

- [x] 2.1 Add a provider architecture contract requiring exactly one GitHub
  HEAD-bound proof entrypoint and no separate full test step; observe RED.
- [x] 2.2 Remove the direct GitHub test step from the canonical template and
  generated workflow.
- [x] 2.3 Remove the test owner script from GitHub's direct provider inventory
  while leaving GitLab unchanged.
- [x] 2.4 Pass focused provider, template-consistency, Actionlint, strict
  OpenSpec, Claim, and quality-audit checks.

## 3. Proof and closeout

- [x] 3.1 Refresh generic parity evidence if the changed carrier set requires it.
- [ ] 3.2 Run exact-HEAD `ethos prove --execute` and require every gate to pass.
- [ ] 3.3 Complete only evidence-backed active tasks and validate the carrier
  for official archive.

## Post-archive transition boundary

Official archive, archive-HEAD parity and proof, current-base refresh if
necessary, candidate land, accepted-root closeout, repo-family closeout, and
owned-Lane retirement are later lifecycle transitions rather than unfinished
active Change tasks.

After accepted local closeout, publish GitHub `dev` and `main` serially and
observe their exact hosted outcomes. A failed main repository-proof job permits
at most one failed-job rerun after host pressure is clear; it does not permit an
automatic retry loop or convert a failure into a pass.

Create the immutable metadata-only closeout record only after those local and
hosted transitions have current evidence. Preserve `CURRENT`, refresh the
records index, and remove only task-owned temporary files. GitLab remains
outside the transition set while intranet access is unavailable.

## Post-change boundary

A green local proof does not claim GitHub success. GitHub branch publication does
not claim main CI success. GitLab remains unverified until intranet access returns.
Host-global proof serialization is a separate successor only if the single proof
still exhibits resource-contention failures.
