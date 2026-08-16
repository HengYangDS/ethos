# Tasks

- [x] **1. Reproduce lifecycle signature bypass.** Prove direct commit-object
  creation ignores effective `commit.gpgsign` and creates an unsigned lane
  materialization commit.
- [x] **2. Centralize generation-time signing.** Make the sole commit-object
  owner inherit signing configuration, verify trust, and preserve repositories
  that do not enable signing.
- [x] **3. Prove generation boundaries.** Cover signed, unsigned-policy,
  untrusted-signer, lane-start success, and pre-effect compensation behavior.
- [x] **4. Derive bounded suffix repair.** Persist an immutable receipt for one
  exact linear old/new commit and integration-ref mapping.
- [x] **5. Apply and resume suffix repair.** Consume the receipt through exact
  Git/Lease CAS and linked-worktree synchronization without a second authority.
- [x] **6. Prove the public recovery.** Cover payload drift, merge rejection,
  stale refs/Lease, interruption recovery, and the real accepted suffix shape.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| command-plane:Lifecycle commit objects inherit repository signing policy | 1 | `tests/unit/mutation/test_git_effect.py` reproduces the direct commit-object boundary. |
| command-plane:Lifecycle commit objects inherit repository signing policy | 2 | `src/ethos/adapters/repo/git_signing.py` is the sole lifecycle commit creator; `tests/unit/mutation/test_git_effect.py` covers enabled and disabled signing. |
| command-plane:Lifecycle commit objects inherit repository signing policy | 3 | `tests/unit/lanes/test_lane_family_profile.py`, `tests/unit/lanes/test_lane_start_carrier_fail_closed.py`, `tests/unit/lanes/test_lane_start_carrier_failure_branches.py`, and `tests/unit/lanes/lease/test_commitment_rebind.py` cover generation, rejection, and compensation boundaries. |
| command-plane:Identity repair supports one receipt-bound linear suffix | 4 | `tests/unit/cli/test_lifecycle_hardening.py::test_repair_identity_derives_one_exact_linear_suffix_receipt` and `::test_repair_identity_derives_and_applies_existing_equivalent_oid_receipt` cover generated and existing replacements. |
| command-plane:Identity repair supports one receipt-bound linear suffix | 5 | `tests/unit/cli/test_lifecycle_hardening.py::test_repair_identity_applies_one_exact_linear_suffix_receipt` and `::test_repair_identity_resumes_same_suffix_receipt_after_worktree_sync_failure` cover exact-CAS apply and resume. |
| command-plane:Identity repair supports one receipt-bound linear suffix | 6 | `tests/unit/cli/test_lifecycle_hardening.py` covers public CLI, receipt tampering, actor/ref/trust drift, and merge rejection; `tests/unit/lanes/lifecycle/test_work_lane_refresh_public_recovery.py` covers the public remediation. |

After Task 6 completes, close this Change only through the governed lifecycle:
execute exact-HEAD full proof; archive that proven HEAD; execute full proof on
the archive HEAD; land and close out that proven archive HEAD; retire the lane;
then rebuild and read back the accepted package-only runtime. These are
post-task effects evidenced by exact receipts and Attestations, not tasks that
may be checked before the effects occur.
