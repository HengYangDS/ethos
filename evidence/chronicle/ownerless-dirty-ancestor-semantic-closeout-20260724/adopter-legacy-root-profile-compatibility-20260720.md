---
subject: ethos:ownerless-dirty-ancestor-semantic-closeout-20260724:adopter-legacy-root-profile-compatibility-20260720
role: evidence
state: active
event: lane_resolution/preserve-retire
target_branch: work/adopter-legacy-root-profile-compatibility-20260720
target_head: b1d0cd2e0a675bf67960b37bf449ce9c158d804c
claim: ownerless-dirty-adopter-legacy-root-profile-compatibility-20260724
---

# Dirty ownerless closeout: adopter legacy root profile compatibility

## Exact observation

The source is a linked, dirty, missing-lease, claim-free accepted ancestor at
`b1d0cd2e0a675bf67960b37bf449ce9c158d804c`. Its tracked binary diff from HEAD
is 6,981 bytes with SHA-256
`5c0ffc8fdb626aa71f3191050f1efee6cf200b1067c6afcc6aeda29fc8e5137e`.
The four tracked paths are the profile contract, repository-governance spec,
profile normalizer, and profile-contract tests. Seven untracked OpenSpec files
carry proposal, design, scope, specification, task, README, and metadata prose;
their SHA-256 values are:

- `.openspec.yaml`: `1ddfe0cbb1d61135d8e1f5fcc791783503766317f0c89a85309f077528044b4c`
- `README.md`: `d7d16de213cb89ab13292d2484d4d153bceca2413e68839441543e458506655c`
- `design.md`: `6292c5fbff7b1fe72a226894782d865f094b283617170ee83eed95c035ceb524`
- `proposal.md`: `6e9d3a506487b5826bd1725fba488cfe4e6c4e2ca62404213ca28b676ea8d765`
- `scope.toml`: `2ea74355af9f9af22610f04ebc8a1a8081e2caaff8b7a23a3aa84921ed716a51`
- delta spec: `e2b2ffaea6467c1582d139629668c0c9159a9411d8ea52b319ca8ad155bfb2d4`
- `tasks.md`: `d16fbfaa6d3f6f348daa5a1d4515d529626c61ef49984dca876e3911db39b9ca`

## Semantic absorption

The dirty intent is narrowly bounded: only a complete former profile envelope
may translate the historical `roots.rules = "."` workaround into
`normative_sources = ["guidelines.md"]`; current or malformed lookalikes remain
invalid, and an already declared normative source is preserved.

Accepted `dev` already carries that behavior. The contract document is
byte-identical to the dirty working copy (Git blob
`878c6a3abe2a55754957abd330fec5c83a37e088`). The accepted normalizer implements
the same predicate and translation with a smaller expression. The accepted test
set contains every dirty test and additionally proves preservation of an
explicit historical normative source. The accepted profile suite passed as part
of the 89-test focused run. The untracked OpenSpec prose is therefore distilled
by this Chronicle; replaying its stale tree or opening a second active Change
would duplicate already accepted behavior.

## Bound decision

After this carrier is accepted, native resolution may select only
`work/adopter-legacy-root-profile-compatibility-20260720` with disposition
`preserve-retire`. It must re-observe the exact dirty content, create a verified
recovery package for every tracked and untracked byte, and only then remove the
source ref and worktree. Drift blocks the effect. Preservation remains recovery
insurance and is not used as the absorption argument.
