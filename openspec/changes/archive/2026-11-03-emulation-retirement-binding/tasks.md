# Tasks

## 1. Runner Docker Ownership

- [x] 1.1 Declare `docker` as a GitHub runner executable and a GitLab runner reference in
      `.config/ci/runners.toml`, and name references in its configuration reference entry. Done
      when the `product_boundary` session reports no `semantic_consumer_orphan` gap. (Proof `h1`
      of `f00e5b876` reported the `docker` executable in `.github/workflows/ci.yml` and the
      `docker` reference in `.gitlab-ci.yml` as orphan consumers; at `882c130c6` the session
      passed in 13 seconds.)

## 2. Supply Binding

- [x] 2.1 Bind the supply digest that the hosted workflow built from the proposal through the CUE
      owner and regenerate the projections. Done when `lane project --check` reports the
      projections conforming and every GitLab supply job selects the new digest and none the
      previous one. (Run `41551197057` built and pushed the image from `b350f258e` in 3 minutes;
      `lane project --check` reported `conforming`; the five GitLab supply jobs select
      `441a02a2…` and none `da1ed80a…`.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land both Changes, close out, bootstrap
  and publish `dev` and `main` to GitHub and GitLab, and confirm both peers' hosted runs pass.
