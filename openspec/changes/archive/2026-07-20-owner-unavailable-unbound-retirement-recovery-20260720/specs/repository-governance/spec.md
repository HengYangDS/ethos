## MODIFIED Requirements

### Requirement: Exceptional unbound Work Lane retirement is exact and accepted-policy-bound

ETHOS SHALL expose a native exceptional route through `ethos lane retire
unbound` for one unbound `work/*` ref only when the current ref is an ancestor
of the accepted branch, has no linked worktree, carries an
accepted-Chronicle-bound active Claim, and matches the supplied expected head.
The target SHALL have either no active lease or exactly one active lease whose
holder, ID, epoch, and expected head remain bound to the current invocation for
native relinquishment. The route SHALL require an accepted, repository-local
Chronicle that contains `lane_retire/unbound_exceptional`, `target_branch:
<branch>`, `target_head: <head>`, and `target_claim: <claim-id>` for the same
exact target. The named local Claim SHALL be byte-identical to its accepted
branch version. One accepted evidence carrier SHALL bind one target; it SHALL
NOT permit a batch effect or apply to another inventory item. Apply SHALL
additionally require explicit authorization, break-glass, and irreversible
confirmation. The route SHALL NOT infer authority from an agent vendor,
session, account, or host-specific path.

#### Scenario: Exact accepted-ancestor residue is inspected

- **WHEN** an operator supplies an unbound `work/*` ref that is an accepted
  ancestor, has no linked worktree and no active lease, and supplies a matching
  accepted Chronicle and Claim, expected head, and reason
- **THEN** dry-run reports `ready_to_retire_unbound_exceptional`
- **AND** it reports the exact observation without deleting the ref
- **AND** it reports that its output does not mint reusable authority.

#### Scenario: One carrier does not authorize another target

- **WHEN** an operator supplies a Chronicle or Claim for a different unbound ref
- **THEN** the command SHALL block the mismatched target before mutation
- **AND** the target SHALL require its own expected head, Claim, Chronicle,
  current observation, and receipt.

#### Scenario: A non-exact or non-accepted target is refused

- **WHEN** the target is linked, has a foreign, ambiguous, stale, or
  head-mismatched lease, is not an accepted ancestor, lacks a
  Chronicle-bound active Claim, has a mismatched expected head, or its Chronicle
  or Claim is missing, unaccepted, generic, stale, or names another target
- **THEN** ETHOS SHALL block the request before any ref mutation
- **AND** it SHALL leave the target ref and any lease intact.

#### Scenario: Exceptional controls are incomplete

- **WHEN** apply omits authorization, break-glass, or irreversible confirmation
- **THEN** ETHOS SHALL block the request before any ref mutation
- **AND** it SHALL report the missing machine-readable control gaps.

#### Scenario: Unavailable source holder is recovered only by exact accepted policy

- **WHEN** a target-specific accepted Chronicle records
  `lease_recovery: owner_unavailable`, the exact active source lease ID, holder,
  epoch, expected head, and a SHA-256 digest of the recorded absolute source
  worktree path, and that path is absent
- **AND** an explicitly confirmed invocation uses
  `--owner-unavailable-recovery` from a different non-empty actor identity
- **THEN** ETHOS MAY revoke only that exact source lease generation through the
  native lease CAS before the existing compare-and-delete transition
- **AND** a present source path, an invalid or mismatched Chronicle lease tuple,
  a missing recovery actor, or a same-holder invocation SHALL block without
  deleting the ref or lease
- **AND** this exception SHALL remain exact-target, receipt-bound, and
  vendor-neutral; process absence, a provider/session label, or a supplied
  holder string alone SHALL NOT authorize takeover.
