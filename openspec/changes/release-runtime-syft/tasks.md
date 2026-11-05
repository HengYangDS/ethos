# Tasks

## 1. Release supply

- [x] 1.1 Require Syft wherever a GitHub job runs the supply chain. Done when the new projection
      test fails on the release runtime job. The new projection test failed first with
      `{"release-platforms": ["vale"]}`.
- [x] 1.2 Stage Syft in the release runtime job. Done when the test and the CI projection tests pass
      and the projection conforms. The release runtime job stages `vale syft`, the projection
      changed only that line, and the 42 CI architecture tests pass with the projection conforming.
