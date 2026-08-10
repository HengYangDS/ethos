# Design

## Retirement observation root

The retirement effect already computes a surviving accepted `control_root`. After the target worktree is removed, all postcondition carriers must be observed through that root: the shared state database, the deleted branch ref, and the target path.

## Runtime wheel provenance

The wheel digest is known before runtime installation. Copy the wheel to `.git/ethos/packages/<sha256>/<filename>` using content equality and immutable permissions, then install from that stable file path. A reused path must match the expected digest. The generated runtime remains content-addressed by wheel digest, Python ABI, and platform.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `repository-governance:terminal retirement receipt` | `1.2` | `linked-retirement-apply` |
| `repository-governance:durable runtime wheel provenance` | `1.4` | `hook-runtime-package` |
