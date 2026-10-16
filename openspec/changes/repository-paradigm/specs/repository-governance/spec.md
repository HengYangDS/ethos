## REMOVED Requirements

### Requirement: Predecessor branch-role tables keep their incumbent meaning

**Reason**: The repository paradigm fixes every branch role name, and `.ethos/release.toml` declares the release mirror, so ETHOS reads no `[branch_roles]` table and no predecessor table generation needs a compatibility reading.

**Migration**: Accepted closeout renames legacy role refs to the standard names; the legacy declarations are then removed from `.ethos/workspace.toml`.
