# Tasks

## 1. Establish the supply identity

- [x] 1.1 Compare the pinned image manifest with the five accepted checkout inputs and confirm the hosted GitLab bootstrap rejects the mismatch.
- [x] 1.2 Build the existing image through the trusted GitHub `dev` workflow at the exact accepted source, then verify its immutable GHCR digest and embedded input manifest.

## 2. Refresh checked projections

- [x] 2.1 Update the CUE image declaration and the GitLab emulator selector to the verified digest; regenerate GitLab YAML and confirm it matches the CUE compiler byte for byte.
- [x] 2.2 Run the affected CI projection and bootstrap tests, strict official OpenSpec validation, format and lint, and diff hygiene on the source patch.

## 3. Keep GitHub's offline supply stable

- [x] 3.1 Reproduce the hosted adopter test failure with a relative UV cache and verify that moving into its temporary repository loses the supplied cache.
- [x] 3.2 Bind GitHub cache paths to the workspace in CUE, regenerate its workflow, and add a regression that rejects relative cache paths.
- [x] 3.3 Run the adopter quality cases against the supplied absolute cache and recheck both Forge projections, strict OpenSpec, formatting, lint, and diff hygiene.
- [x] 3.4 Reproduce the cold-cache offline-solve failure, replace test-time lock resolution with a checked-in project/lock fixture, and retain the missing-lock and lock-drift negative cases.
- [x] 3.5 Recheck the full adopter quality suite, CI projections, strict OpenSpec, formatting, lint, and diff hygiene for the revised source.
- [x] 3.6 Observe the exact-SHA GitLab verification failure and its retained `mise` download diagnostic; distinguish it from Runner interruption or a test assertion.
- [ ] 3.7 Bake the locked native gate tools into the immutable image, bind every copied input to its context allowlist and manifest, reject hosted cache misses before network access, and prove the no-network image smoke.
- [ ] 3.8 Build and verify the new trusted image, pin its digest, regenerate both provider projections, and recheck the full local quality boundary.
- [ ] 3.9 Keep all three MCP conformance transports and their per-call limits, scope a finite aggregate timeout to the composite test, and verify it in hosted GitHub CI.

## 4. Accept and verify hosted delivery

- [ ] 4.1 Commit and prove the revised source at its exact HEAD, then accept and install it through the native lane and runtime transitions.
- [ ] 4.2 Publish the accepted `dev` source to each selected Forge through fresh receipts and verify all required jobs on that exact commit.
- [ ] 4.3 Publish verified `main` through fresh receipts and confirm both remote refs, leaving the Change active until hosted evidence is complete.
