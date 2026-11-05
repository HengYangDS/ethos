# Tasks

## 1. Merge and rebind

- [x] 1.1 Resolve the refresh conflicts. Done when no conflict marker remains, `changelog_errors`
      reports nothing, and the CI projection conforms. All three hold after the merge.
- [ ] 1.2 Bind a supply image built from the merged locks. Done when the hosted `supply_image`
      workflow built it from this lane and every GitLab supply job selects its digest.
