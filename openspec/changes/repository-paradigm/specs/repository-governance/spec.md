## REMOVED Requirements

### Requirement: Predecessor branch-role tables keep their incumbent meaning

**Reason**: The repository paradigm fixes every branch role name. A `[branch_roles]` table declares only the release mirror and the canonical sibling worktrees, each optional with its default, so no predecessor table generation needs a compatibility reading.

**Migration**: Accepted closeout renames legacy role refs to the standard names; the legacy declarations are then removed from `.ethos/workspace.toml`.
