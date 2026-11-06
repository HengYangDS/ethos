# Tasks

## 1. Supply move

- [x] 1.1 Move both `uv.lock` files to the newest releases published before the 24-hour cutoff.
      Done when `uv lock --check` passes for both and the fixture lock test passes. The cutoff
      2026-11-05T06:31:08Z moved authlib 1.9.4, coverage 7.17.2, filelock 4.2.9, platformdirs 4.14.5,
      ty 0.0.97 and typing-inspection 0.4.5, and coverage 7.17.2 in the fixture; both checks pass.
- [x] 1.2 Move Syft and Grype in `.config/mise/` to releases at least 24 hours old. Done when the
      locked tools install, `node.exe` is checked again with the new Syft, and the Syft pin test
      names the new version. Syft 1.57.0 and Grype 0.121.2 are locked for 10 targets and install.
      Syft 1.57.0 still catalogs `node` but not `node.exe`, so the declaration stays; the pin test
      names 1.57.0, and 29 tests pass.
- [x] 1.3 Rebuild and bind the CI supply image. Done when the image's manifest matches the moved
      files and the bound digest is in `.config/ci/pipeline.cue`. Supply run 42176217472 built
      `sha256:36acefde2cda…` from `690e75069`, and all 5 GitLab jobs select it.
