# Tasks

## 1. Merge and rebind

- [x] 1.1 Resolve the refresh conflicts. Done when no conflict marker remains, `changelog_errors`
      reports nothing, and the CI projection conforms. All three hold after the merge.
- [x] 1.2 Bind a supply image built from the merged locks. Done when the hosted `supply_image`
      workflow built it from this lane and every GitLab supply job selects its digest. Run
      42079903450 built `sha256:f9f00948` from `bfc55aeb8`, which merges dev `fa6ace8ec` (Python
      day-old lock and quality fixture lock), receipts and lease-holder. All 5 GitLab supply jobs
      select it, none selects `6afacee6`, and the projection conforms.
