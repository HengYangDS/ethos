## 1. Runtime contract and bootstrap

- [ ] 1.1 Add a single repository-owned Python/uv runtime bootstrap with checkout-bound `build/runtime/venv` and explicit host-or-CI cache behavior.
- [ ] 1.2 Route the Work Lane runner, Python owner scripts, local fallback CI, and installed Git hooks through the bootstrap or explicit bounded interpreter path.
- [ ] 1.3 Remove active root `.venv` fallback and bare producer `uv run` paths from product-owned executable surfaces.

## 2. Topology enforcement and adopter projection

- [ ] 2.1 Extend generated-artifact policy and entrypoint audit to reject active root environment fallback and bootstrap-bypassing uv producers while retaining legacy root environments as non-authoritative residue.
- [ ] 2.2 Align local-state audit, command payloads, canonical architecture/reference docs, and adoption scaffold templates with the hybrid runtime boundary.
- [ ] 2.3 Update packaged policy mirrors and generated declarations required for installed-runtime parity.

## 3. Verification and lifecycle

- [ ] 3.1 Add focused tests for checkout isolation, override precedence, hook runtime selection, owner-script routing, topology audit failures, and adoption projections.
- [ ] 3.2 Run OpenSpec strict validation, focused tests, topology audit, and full head-bound proof/local fallback CI on a stable lane head.
- [ ] 3.3 Bind claim and evidence, land through `candidate/dev`, execute accepted-root closeout, retire only this owned Work Lane, and record remote publication as deferred.
