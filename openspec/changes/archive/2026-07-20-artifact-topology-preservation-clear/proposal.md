## Why

The accepted artifact-topology source lane has been semantically absorbed and
natively retired, but its safety preservation package remains. The package is
not a cache and must not be removed with `rm`; leaving it indefinitely after its
only parity metadata is superseded would violate terminal residue reduction.

## What Changes

- Bind one exact decision id, package path, manifest SHA-256, prior receipt, and
  stale parity-patch SHA-256 to an accepted current-proof comparison.
- Authorize only the existing native `lane_resolution/clear-preservation`
  command after this carrier's local closeout.
- Preserve the original decision and receipt, and retire this temporary carrier
  after its single clearance effect is verified.

## Capabilities

- `repository-governance`: subject=artifact-topology-preservation-clear; reuse=extend; change=modify; facet:lifecycle=validation,archive,release; facet:surface=docs,openspec,evidence; facet:authority=source,test,openspec,claim,evidence.

## Out Of Scope

- Any other package, branch, worktree, lease, receipt, remote, hosted CI,
  broad retention sweep, raw deletion, or source reconstruction.
