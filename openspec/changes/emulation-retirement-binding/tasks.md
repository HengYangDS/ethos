# Tasks

## 1. Runner Docker Ownership

- [ ] 1.1 Declare `docker` as a GitHub runner executable and a GitLab runner reference in
      `.config/ci/runners.toml`, and name references in its configuration reference entry. Done
      when the `product_boundary` session reports no `semantic_consumer_orphan` gap.

## 2. Supply Binding

- [ ] 2.1 Bind the supply digest that the hosted workflow built from the proposal through the CUE
      owner and regenerate the projections. Done when `lane project --check` reports the
      projections conforming and every GitLab supply job selects the new digest and none the
      previous one.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land both Changes, close out, bootstrap
  and publish `dev` and `main` to GitHub and GitLab, and confirm both peers' hosted runs pass.
