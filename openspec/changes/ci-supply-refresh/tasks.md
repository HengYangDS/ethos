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
