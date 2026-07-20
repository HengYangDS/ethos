# Exceptional unbound Work Lane retirement — quality zero exceptions successor v2

event: lane_retire/unbound_exceptional
target_branch: work/quality-zero-exceptions-successor-v2-20260719
target_head: 943a5e1e373b009f02533ff22815e8bca32b3157
target_claim: quality-zero-exceptions-successor-v2-unbound-retirement-20260720
lease_recovery: owner_unavailable
source_lease_id: lease:03c8fb14-e616-4fc7-9592-bcba283fcdc5
source_lease_holder: agent:codex:session:quality-zero-exceptions-successor-20260719
source_lease_epoch: 1
source_lease_expected_head: 943a5e1e373b009f02533ff22815e8bca32b3157
source_worktree_path_sha256: c580afbd6aea7d9f468e61d46120ec439172f555202ac6c4702378e0f9452af0
source_worktree_absent: true

## Fact

At acceptance of this policy carrier, the target ref is an unbound accepted
ancestor; its source worktree path is absent; and the exact active lease tuple
above remains bound to an unavailable source holder. The target head contains no
unique delta outside accepted history.

## Boundary

This record authorizes no generic takeover or manual deletion. It can be
consumed only by the native `ethos lane retire unbound` transition with the
exact branch/head, explicit owner-unavailable recovery mode, and all ordinary
exceptional controls. It grants no authority from a vendor, account, session,
host path, process absence, or this policy carrier to any other lane.

## Stop conditions

Preserve the target if the ref/head, accepted relation, Claim, Chronicle bytes,
lease ID/holder/epoch/expected head, source path, protected refs, CAS result, or
postconditions drift. Do not substitute raw Git or SQLite deletion.
