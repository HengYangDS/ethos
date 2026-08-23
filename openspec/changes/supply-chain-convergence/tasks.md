# Tasks

- [x] **1. Inventory and RED.** Enumerate every controlled direct package,
  downloaded binary, action, image, runtime, checksum, and provider projection;
  add focused checks that expose stale, duplicate, orphaned, and divergent
  declarations.
- [x] **2. Native package convergence.** Upgrade Python and Node direct
  declarations to current stable releases through uv and npm and regenerate
  their exact locks.
- [x] **3. Binary and provider convergence.** Upgrade external tools, checksums,
  action SHAs, and container digests in their unique owners; regenerate GitHub
  and GitLab projections.
- [x] **4. Incumbent deletion.** Remove duplicated installer defaults and any
  current mutable version prose or provider-local literal subsumed by the
  selected owners; prove repository-wide reference closure.
- [x] **5. Focused proof.** Run format before lint, then supply-chain inventory,
  configuration, CI projection, release, and OpenSpec strict validation gates.
- [x] **6. Terminal proof and closeout.** Freeze the candidate, repeat current
  stable resolution, run full HEAD-bound proof and release compatibility once,
  archive through the public lifecycle, land by exact CAS, and verify accepted
  package/runtime projection.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | ---: | --- |
| `quality:Controlled supply-chain identities have one owner` | 1 | `tests:supply-chain-inventory-red-green` |
| `quality:Controlled direct inputs use stable current releases` | 2 | `uv-lock:npm-lock:current-stable` |
| `quality:Environment tools do not become repository authority` | 4 | `audit:no-parallel-environment-owner` |
| `quality:Supply Chain Evidence` | 5 | `gates:head-bound-supply-chain-evidence` |
