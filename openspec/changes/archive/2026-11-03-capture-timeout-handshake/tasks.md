# Tasks

## 1. Timeout capture tests

- [x] 1.1 Start the timeout of both tests after the child's readiness handshake. Done when both
      pass, and still pass with a 2-second sleep before the child writes, where the previous tests
      fail. With the sleep the previous four timeout cases failed with an empty capture, as in
      pipeline 14011, and the new ones pass; the file's 23 tests pass.

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
