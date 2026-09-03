## 1. Freeze The Semantic Boundary

- [x] 1.1 Add RED tests proving canonical semantic bytes use the closed value grammar, UTF-16 key order, UTF-8 encoding, and no presentation whitespace; run the focused kernel test and observe the intended failures.
- [x] 1.2 Add RED tests proving proof-floor identity, independent-verification
  digest/signature bytes, and control-replacement subject identity use the same
  kernel owner; add public-boundary tests proving unconsumed RuleSet, compiled-
  policy, skill-registry, and source-budget inventory checksums are absent; run
  the focused tests and observe the intended failures.

## 2. Replace Duplicate Identity Owners

- [x] 2.1 Implement the kernel canonical-byte projection and make `canonical_json_digest` hash only those bytes; verify focused kernel tests pass.
- [x] 2.2 Migrate all identified semantic/admission consumers, delete
  `stable_digest`, delete unconsumed checksum projections, and verify repository-
  wide references are closed while native-byte owners remain.
- [x] 2.3 Add the canonical-byte invariant to the product contract, retire the
  stale source-budget inventory-checksum obligation without changing its
  deterministic measurement facts, and preserve content-addressed raw-byte and
  presentation ownership; verify documentation and OpenSpec checks pass.

## 3. Prove And Close The Change

- [x] 3.1 Audit the selected Attestation set and live validity-bounded signed
  receipts for current compatibility, then run focused semantic, proof-floor,
  independent-verification, control-replacement, skill-registry, and source-
  budget tests plus strict OpenSpec validation.
  Evidence: all 907 JSON records in `refs/ethos/attestations-set` validate under
  the current Attestation contract; the effective independent-verification
  policy is disabled, no receipt is explicitly selected, and the repository
  receipt root is absent. The protected system provider configuration exists
  but is unreadable to this process identity, so no claim is made about
  unselected provider-store contents. The focused semantic/downstream suite
  passed 205 tests, and OpenSpec 1.11.0 strict validation passed.
- [x] 3.2 Run repository-wide reference, lint, type, architecture, and
  exact-HEAD full proof; update task evidence only after the frozen boundary
  passes.
  Evidence: the isolated local-CI closure passed 2,008 tests with one skip plus
  build, install-smoke, supply-chain, static, architecture, and repository
  checks. Exact HEAD `d418998210c0b1e67a9d8d7a8866518426101968`
  (`dffe7eab90de807611797afd72708abb1621a48c`) then passed all 24 full-proof
  gates and issued Attestation
  `53d36ead3ed316f1ecb9b3be1c24f88ca33281905d7e7de4fa601a99354a6240`.
- [x] 3.3 Freeze official archive as the next bounded transition. The public
  archive dry-run rejected only this previously incomplete task set; no product
  or specification gap remained. Archived
  exact-HEAD reproof, candidate and accepted exact CAS, fresh immutable
  package-only runtime readback, declared peer publication, and residue-free
  Work Lane retirement remain mandatory post-archive closure under the terminal
  plan; this checklist does not claim those later effects have occurred.
