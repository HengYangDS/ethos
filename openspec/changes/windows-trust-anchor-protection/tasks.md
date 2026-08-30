## 1. Contract and RED

- [x] 1.1 Specify native trust-anchor protection and validate the Change with
  `openspec validate windows-trust-anchor-protection --strict`.
- [x] 1.2 Preserve the exact Hosted Windows failure as RED and add focused tests
  that distinguish protected and foreign-writable ACL observations.

## 2. Unique owner repair

- [x] 2.1 Replace the cross-platform mode-bit assumption at the Git-object trust
  owner and verify focused trust tests pass.
- [x] 2.2 Make anchor creation and the package-smoke fixture establish the same
  native protection and verify the installed-package smoke regression passes.

## 3. Closure

- [x] 3.1 Pass strict OpenSpec validation, focused tests, Ruff, types,
  module-layout, and repository-hygiene checks.
- [ ] 3.2 Freeze a signed source commit and pass exact-HEAD full proof.
- [ ] 3.3 Archive through the official transition, pass archived exact-HEAD
  proof, install/read back the accepted runtime, and publish dev then main to
  GitHub and GitLab.
- [ ] 3.4 Confirm Linux, macOS, Windows 3.12/3.13/3.14, package, quality,
  security, and both GitLab pipelines pass for the exact accepted object, then
  retire the Work Lane with no ref/worktree/Lease residue.
