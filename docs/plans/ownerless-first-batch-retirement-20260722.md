---
subject: ethos:ownerless-first-batch-retirement-20260722
role: plan
state: active
relations:
  derives_from: all-lanes-authorized-closeout-20260718
---

# Ownerless First-Batch Retirement — 2026-07-22

Status: the original eight-row carrier is accepted and executed. This revision
binds a three-row clean-ancestor extension; native retirement is authorized
only after this exact revision completes normal candidate and accepted-root
closeout.

Purpose: perform the first bounded retirement cohort before any valid-owner
lane is considered. This carrier is deliberately limited to clean, linked,
missing-lease lanes whose exact heads are accepted-root ancestors and whose
current observation reports no claim binding or dirty residue.

## Exact cohort

| Branch | Head | Semantic finding | Proposed disposition |
| --- | --- | --- | --- |
| `work/adopter-profile-migration-20260720` | `b1d0cd2e0a675bf67960b37bf449ce9c158d804c` | Current accepted behavior is already represented by the archived adopter-profile carrier. | retire |
| `work/integrate-archived-openspec-identifier-normalization-successor-v5-20260720` | `8b59c8f17e2952ad1a15dd03a7e7432802e04d3a` | Accepted ancestry contains the historical identity-normalization result. | retire |
| `work/integrate-openspec-archive-identifier-normalization-successor-v4-20260720` | `f05bdacd84c0e7ed23daa75079e74eef1725eb99` | Accepted ancestry contains the historical identity-normalization result. | retire |
| `work/owner-unavailable-unbound-retirement-recovery-20260720` | `32b3be4d12e121af982a58b5423a1121814fa9f2` | Recovery mechanics are accepted; this source lane has no residual work. | retire |
| `work/t8-module-layout-test-matrix-compression-20260719` | `63f62464b3015f9b09e41f163fd0a2a399c9bb40` | Empty, expired local setup lane; no uncommitted or semantic residual was observed. | retire |
| `work/ddwg-profile-bootstrap-bridge` | `25e6ca1ece57a934dd47c5e4970d107945fc5c2a` | Current profile normalization supersedes this bootstrap bridge. | retire |
| `work/20260721-github-runner-isolation` | `e7c29a2213f35b6bfbfe7e77a33e47121b5f0c4c` | Accepted runner controls supersede this clean ancestor. | retire |
| `work/github-timeout-source-budget` | `9271c46d63064dfdc10651f867bcd19aad8dce63` | Accepted source-budget governance supersedes this clean ancestor. | retire |
| `work/budget-contract-v2-carrier-resource-boundary-successor-20260723` | `102afdf3b0248b58bfde7aa2d0865109406c2ede` | The exact parity-only commit is in accepted ancestry; its historical parity blob has since been refreshed by accepted commits. | retire |
| `work/gitlab-runner-resilience` | `ffe5bf56719a2e218d74ac1a3fd35ebe777f5136` | The exact CI hardening commit is in accepted ancestry; production blobs remain represented and the test projection has only been superseded by later accepted coverage. | retire |
| `work/20260721-gitleaks-cache-resilience-v2` | `408e06eeadae7326ada2fc4f468612971b35031a` | The exact verified-artifact commit is in accepted ancestry; the installer blob remains represented and its test coverage has only been superseded by later accepted coverage. | retire |

For the three-row extension, semantic absorption is established by exact Git
ancestry, not by age, path existence, or an archive label. At observation
baseline `24d6edcf31ee94c1a10b6abb022298e290242380`, each named target HEAD is an
ancestor of accepted `dev`. The individual Chronicles additionally bind the
target commit paths to identical or later accepted blobs. Native resolution
must repeat the ancestry, cleanliness, lease, claim, and exact-HEAD checks
before effect.

## Preconditions and boundaries

1. Every effect is one target at a time: fresh `lane status`, decision, apply,
   receipt, and re-observation. Any head, lease, claim, path, or cleanliness
   drift stops that target.
2. This carrier does not grant ownership over valid-lease lanes and does not
   cover a dirty lane, a diverged lane, a remote mutation, or hosted evidence.
3. Each target has its own Chronicle below, intentionally naming the exact
   branch and HEAD. The Chronicles become usable only after this carrier has
   passed normal proof, landed, and completed accepted-root closeout.
4. The pre-existing `lane_resolution_manifest_receipt_mismatch` is preserved as
   a separate integrity defect. No package is cleared, overwritten, or ignored
   by this cohort.

## See Also

- [Authorized Work Lane Cohort Closeout](all-lanes-authorized-closeout-20260718.md)
- [All Work Lanes Convergence Program](all-work-lanes-convergence-program-20260716.md)

See also: these carriers define the accepted-decision boundary for the exact effects above.
