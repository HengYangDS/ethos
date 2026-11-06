# Tasks

## 1. Stale image refusal

- [x] 1.1 Specify the refusal with failing tests. Done when tests fail for a manifest input that
      differs from its bytes at the bound source commit, and pass for an unchanged one. The tests
      failed first on the missing module.
- [x] 1.2 Record `gitlabImageSource` and check it in the CI projection gate. Done when the tests
      pass and the current binding records the commit that built it. `gitlabImageSource` names
      `690e75069`, which built `sha256:36acefde2cda…`. With one input changed, the CI projection
      check refuses `supply_image_stale:package-lock.json` and names the route.
- [x] 1.3 Keep GitLab's bootstrap tool list equal to the Dockerfile's. Done when a projection
      test compares the two lists and the projection conforms. The parity test passes on the
      identical lists, and 124 CI architecture tests pass.
