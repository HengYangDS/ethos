## Context

Distinct ETHOS source trees, wheels, and runtimes currently collide under one
reused package version even though lower-level hashes differ.

## Decisions

### One product authority, several exact identities

`VERSION` owns canonical SemVer. Python and npm metadata are projections.
`packaging.version.Version` owns PEP 440 parsing and comparison; npm owns its
package-version validation. ETHOS binds product version, source commit/tree,
wheel digest, runtime digest, channel, and acceptance without conflating them.

Accepted builds use the exact normalized product version. Every other build
adds PEP 440 development and commit/tree local identity. Git SHA remains source
provenance, never product SemVer.

### Runtime and release admission consume immutable evidence

The runtime digest covers build identity, wheel bytes, interpreter/ABI, operating
system, CPU architecture, dependency lock, and executable bytes. `CURRENT`
selects one content-addressed runtime and currentness validates the complete
manifest.

Accepted version reuse is checked against immutable Git and Attestation facts.
Forge state is an optional projection, so local-only and configured Forge
topologies share the same identity semantics without a release ledger.

## Rejected alternatives

- Static versions in `pyproject.toml` or npm manifests: parallel owners.
- Local SemVer/PEP 440 parsers: duplicate standards.
- Git SHA in product SemVer: provenance/meaning conflation.
- Version-only runtime selection: cannot prove equal bytes.
- Compatibility emission of `0.1.0a2`: perpetuates ambiguous builds.

## Migration and risks

Builds fail closed without exact source identity. Projection checks reject
manifest drift. Historical runtimes remain immutable history but cannot become
current. Replace literals, verify unique development wheels and full manifests,
then prove and admit one newly versioned package-only runtime.

The source budget is calibrated to the smallest hundred-line ceilings that
admit the post-audit candidate: product 42,800, tests 38,200, and global 93,700.
This is not a claim that line count proves structural quality. Before raising
the boundary, the Change deleted duplicate test acceptance, an unused prewrite
worktree scan, per-worktree repetition of complete runtime binding, and repeated
Python subprocess observations. The remaining growth carries BuildIdentity,
content-addressed runtime, manifest-v5 architecture binding, exact activation
and compensation, and package-only invariants. Semantic duplication, mixed
ownership, package topology, coupling, and policy self-relaxation belong to the
dependency-linked `quality-policy-authority` successor, where parent policy
evaluates the candidate tree; they are not encoded as exceptions in this
version Change.
