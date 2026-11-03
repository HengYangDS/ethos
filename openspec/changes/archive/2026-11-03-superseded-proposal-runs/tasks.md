# Tasks

## 1. Hosted supersession

- [x] 1.1 Give the GitHub workflow its concurrency group. Done when a structural test shows the
      group is the workflow and ref only for a push of a proposal ref, the workflow and run ID for
      every other event, with `cancel-in-progress: true`, and the test failed before the change.
      The test failed with no group and passes with it; the 79 CI architecture and projection tests
      pass.
- [x] 1.2 Cancel superseded GitLab proposal pipelines only. Done when a structural test shows every
      job is interruptible, the proposal rule cancels interruptible jobs on a new commit and the
      rules for `dev`, `main` and merge requests cancel nothing, and the test failed before the
      change. The test failed on the missing `interruptible` default and passes after.
- [x] 1.3 Record the change in the changelog. Done when the unreleased Changed section names it.

## 2. Specification

- [x] 2.1 Write the `quality` delta. Done when strict validation and the cumulative archive
      simulation pass. A new requirement holds the supersession, since the existing one would pass
      500 characters; both pass, and all 12 specifications stay valid.

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
