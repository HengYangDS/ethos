# Tasks

## 1. Ownership

- [x] 1.1 Map each path that the CI projection declaration names as a template to the Forges of
      the pipeline files it produces, and use that mapping in patch admission and in the
      repository semantic closure. Done when an identity used by a declared template and its
      projection is owned by the projection's runner declaration, and the existing runner cases
      pass unchanged.
- [x] 1.2 Cover the rule in patch admission and in the semantic closure, each with a declared
      template and an undeclared one. Done when the declared cases fail on the parent tree's
      behaviour and all four cases pass on the lane.

## 2. Specification and records

- [x] 2.1 Write the `repository-governance` delta. Done when strict validation passes.
- [x] 2.2 Add the `declared-parameters` and `pipeline-template-ownership` changelog entries and the
      DR-0010 entry for the landed figures. Done when the documentation gates pass.

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass;
  the archive commit changes only OpenSpec documents, which its own proof checks.
