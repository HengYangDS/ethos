# Tasks

## 1. Supply Binding

- [x] 1.1 Bind the published supply digest through the CUE owner and regenerate the projections.
      Done when `lane project --check` reports the projections conforming and every GitLab supply
      job selects the new digest and none the previous one. (Run `41260025679` built and pushed the
      image from `e5c63cd0e` in 3 minutes; `lane project --check` reported `conforming`; the five
      GitLab supply jobs select `f9a083b6…` and none `3983dae4…`.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to GitHub and GitLab, and confirm both peers' hosted runs pass.
