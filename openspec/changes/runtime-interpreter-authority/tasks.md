## 1. Establish the semantic failure

- [x] 1.1 Add RED tests proving a directly invoked admissible interpreter is
  selected without candidate discovery or installation.
- [x] 1.2 Add RED cases proving an incapable framework/base candidate falls back
  only to installed congruent images, while absent, virtual, outside-prefix, or
  identity-incongruent candidates fail before effects.
- [x] 1.3 Reproduce the empty-cache host failure and add RED contracts proving
  that the invocation environment supplies dependency bytes while the base
  interpreter supplies only the native image.
- [x] 1.4 Add a RED relation contract proving dependency bytes cannot cross ABI,
  version, implementation, or architecture identities before copying begins.

## 2. Replace the interpreter authority boundary

- [x] 2.1 Extend Python fact observation with executable and base-executable
  identity and make native Python path equality owned by that module.
- [x] 2.2 Replace managed-Python selection and installation with base-first
  admission plus read-only enumeration of already-installed candidates through
  the authenticated invoking Python.
- [x] 2.3 Migrate runtime post-observation to the same path-identity owner and
  delete every active runtime-materialization reference to `uv python install`
  or managed-interpreter selection.
- [x] 2.4 Restore one lock-current dependency-byte supply owner, reuse it from
  runtime materialization and package acceptance, and delete the duplicate
  delivery supply and cache authority.
- [x] 2.5 Keep package-only successor construction on its validated immutable
  closure and exact content-addressed wheel without requiring source supply.

## 3. Prove the bounded fix

- [x] 3.1 Run focused input-resolution, Python-environment, dependency-supply,
  Python-image, runtime-effect, hook
  activation, and package-acceptance tests across the available native host.
- [x] 3.2 Add a RED hosted-projection contract, provision the GitHub matrix's
  native image before activation, and run the same package-only host-conformance
  owner from the digest-pinned GitLab image.
- [x] 3.3 Run Ruff, typing, module-layout, source-budget, strict OpenSpec, and
  repository-wide retired-reference checks.
- [x] 3.4 Run the real package-only host-conformance owner and verify runtime
  activation completes from the repository's lock-provisioned environment.

## Lifecycle Transition Boundary

After every task above is complete, the implementation requires one signed
commit and exact-HEAD full proof before official archive. Archive creates a
distinct signed HEAD that then requires post-archive proof, candidate and
accepted exact CAS, fresh immutable package-only runtime activation and
readback, publication of that exact accepted object to every declared peer in
deterministic order, hosted-CI observation, and retirement of this Work Lane
and its owned resources. These are mandatory terminal state transitions after
the checklist, not self-referential pre-commit tasks, and MUST NOT be claimed
before their exact observations exist.
