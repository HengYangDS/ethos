# Tasks

## 1. GitLab artifacts

- [x] 1.1 State that GitLab archives hold evidence only. Done when the new projection test fails on
      `build/artifacts/python/` in the verify job. The new test failed first with
      `{"ethos:verify": ["build/artifacts/python/"]}`.
- [x] 1.2 Drop the Python distributions from the GitLab verify archive. Done when the test and the
      CI projection tests pass and the projection conforms. With the path dropped and
      `.gitlab-ci.yml` reprojected, the new test and the 41 CI architecture tests pass, and the
      projection conforms.
