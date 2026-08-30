## 1. Contract and Regression

- [x] 1.1 Define the distribution and repository-governance deltas and verify `openspec validate supply-chain-version-convergence --strict` passes.
- [x] 1.2 Update current-version and bundled-OpenSpec regression expectations and verify they fail against the old authorities.

## 2. Minimal Supply and Version Change

- [x] 2.1 Advance `VERSION` and npm version projections to `0.2.0-alpha.3` and verify the version-owner tests pass.
- [x] 2.2 Upgrade exact OpenSpec supply and lock data to 1.11.0 and verify package, lock, adapter, and official CLI identities agree.
- [x] 2.3 Advance current Python, npm, Syft, uv CI, and Node compatibility supply owners to verified stable releases and verify their owner/projection tests pass.
- [x] 2.4 Close the alpha.2 changelog section, record alpha.3 under Unreleased, and verify documentation checks pass.

## 3. Proof and Closeout

- [x] 3.1 Run focused version, supply-chain, build, install, CLI, and OpenSpec gates and record passing results.
- [ ] 3.2 Create the signed source commit and verify exact-HEAD full proof succeeds.
- [ ] 3.3 Archive the official Change, verify post-archive full proof, promote the exact object to accepted, and verify the installed runtime identity.
- [ ] 3.4 Retire the Work Lane and verify its ref, worktree, and Lease no longer exist.
