## ADDED Requirements

### Requirement: Scoped campaign closeout selection
ETHOS SHALL allow `ethos campaign closeout --campaign <campaign-id> --json` to evaluate one named campaign without treating another campaign’s active or planned state as an implied blocker. The command SHALL remain read-only, SHALL preserve the requested campaign selector in its report, and SHALL return a missing-campaign gap when the selector cannot resolve.

#### Scenario: One active campaign is selected
- **GIVEN** a repository contains two campaign manifests and one unrelated campaign remains active
- **WHEN** an operator runs `ethos campaign closeout --campaign repo-first-worktree-governance-v2 --json`
- **THEN** the campaign package contains only `repo-first-worktree-governance-v2`
- **AND** its readiness does not derive a gap from the unrelated campaign
- **AND** the report identifies `repo-first-worktree-governance-v2` as the requested selector.

#### Scenario: A campaign selector is unknown
- **WHEN** an operator runs `ethos campaign closeout --campaign absent-campaign --json`
- **THEN** the command reports `campaign_missing:absent-campaign`
- **AND** it does not claim local readiness for the absent campaign.

### Requirement: Repo-first worktree governance campaign boundary
ETHOS SHALL model repo-first worktree governance v2 as a dedicated strict-serial campaign. Its bootstrap SHALL record Git as authority for refs, history, and linked-worktree registration; ETHOS as authority for policy, ownership, admission, receipts, and lifecycle gates; and an optional future backup system only as an independent backup mechanism for sealed records. The bootstrap SHALL not authorize cross-repository lifecycle transfer, foreign-lane mutation, or dirty-state retirement.

#### Scenario: Bootstrap exposes independent future slices
- **GIVEN** the repo-first worktree governance campaign is active
- **WHEN** `ethos campaign status --campaign repo-first-worktree-governance-v2 --json` runs
- **THEN** it exposes one active bootstrap step and ordered planned successor steps
- **AND** every successor declares its own OpenSpec change, Work Lane, Claim, and planned closeout record
- **AND** the campaign topology is `strict_serial`.

#### Scenario: Foreign lane remains outside bootstrap authority
- **GIVEN** a visible linked Work Lane has no owned lease or owner handoff for the bootstrap holder
- **WHEN** the bootstrap campaign is evaluated
- **THEN** the campaign does not authorize moving, retiring, deleting, or preserving that lane
- **AND** the lane remains an observation requiring its own holder-bound or accepted exceptional process.

### Requirement: Repo-first preservation topology contract
ETHOS SHALL reserve repository-adjacent topology for future governed worktree and record operations as `<projects-root>/<repo>-worktrees/<yyyymmdd>-<task-slug>` and `<projects-root>/<repo>-records/{.staging,evidence,recovery}/<timestamp>-<purpose>`. Status labels such as sealed, restorable, legacy-v1, or unverified SHALL be recorded in manifests rather than introduced as top-level topology classes.

#### Scenario: Topology contract does not create a second lifecycle authority
- **WHEN** a later campaign slice uses the topology contract to plan preservation or recovery
- **THEN** Git remains the authority for committed refs and worktree registration
- **AND** ETHOS remains the authority for admission, lifecycle, receipt, and retirement decisions
- **AND** the topology alone does not authorize a filesystem deletion or restore.
