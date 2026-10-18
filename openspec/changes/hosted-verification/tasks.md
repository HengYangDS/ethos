# Tasks

## 3. ETHOS conformance

- [ ] 3.8 Build the CI supply image that runs as its unprivileged user through the GitHub supply job, pin its digest in the CI model and accept the GitLab pipeline on it.

## 7. Hosted Execution and Publication

- [ ] 7.3 Requalify hosted supply failure after repairing lost timeout output; retain native diagnostics and clear prior reports before any proof.
  - [x] 7.3.1 Report the bootstrap failure that a staging cleanup error masks in native tool supply; done when a supply failure followed by a cleanup failure reports both (windows-latest run 38658885061 printed only the cleanup's WinError 32 on the staged `mise.exe`).
- [ ] 7.4 Consolidate hosted full execution and fail-closed required checks; observe external-link health separately without starving proof reports or hiding its failure.
  - [ ] 7.4.1 Decide how GitLab external-links handles intermittent github.com 503 responses from the intranet egress (different links each run in pipelines 10526/10575/10576; GitHub-hosted runs pass); done when GitLab external-links passes or its provider scope is recorded with a rationale.
  - [ ] 7.4.2 Admit the Linux `lsof` record of a process or descriptor that exits during the open-file scan, which carries no type, device or inode, while every other unreadable record keeps the observation incomplete; done when the GitHub hosted quality job passes the reviewed-disposal retirement cases at the fix head (they were its only failures in runs 39090251125 and 39092249050).
- [ ] 7.5 Qualify and deliver the exact single-execution CI candidate.
- [ ] 7.9 Qualify the rootless dual-provider successor through exact proof, installed runtime and hosted observation.
- [ ] 7.11 Qualify both CUE-generated Forge projections through current hosted runs.
  - [x] 7.11.1 Qualify compatible operator mise supply and native PowerShell environment isolation through exact source and runtime delivery.
  - [ ] 7.11.2 Qualify the GitHub-hosted-only matrix and source-derived emulator mapping; retire dedicated-runner and inherited-hook projections, verify GitLab digest-bound supply, and distinguish the bootstrap transport failure in 5.11 from version admission and ACL conformance. Fault-test each selected Forge's complete required graph on a cold runner while the peer's registry and release endpoints are unavailable; current ETHOS and AIGW GitLab images depend on GHCR.
  - [x] 7.11.3 Keep the GitLab verify archive within the instance artifact-size limit, which the project owner cannot raise, by retaining raw Allure results only on GitHub; done when a dev/main GitLab verify job uploads its archive and passes (job 52714 at `dadf4c95b` uploaded 60.63 MiB and passed; refused with 413 at `365fbffda` and `aa79ed28b`).
  - [x] 7.11.4 Rebuild the Linux ARM64 supply image for the moved CI projection policy and Debian's curl security update, then rebind its digest; done when a dev/main GitLab ethos:commit-policy job passes the supply input check (dev pipeline 10872 at `c658ba060` passed it and ethos:verify; refused with ci_supply_input_mismatch since `743304426`; build failed on the stale curl pin in run 38614312901).
- [ ] 7.12 Qualify semantic CI job partitions and native successful-pipeline merge enforcement.
- [ ] 7.13 Qualify runner capacity and dependent-pipeline observation with bounded acquire, terminal readback and original-state restoration; distinguish paused, offline and tag mismatch without repository-specific VM control.

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out and publish.
- Task 3.8 moved verbatim from `repository-paradigm` on 2026-10-18, so that Change could archive while its GitLab acceptance continues here.
