# Tasks

## 1. Checks at their owners

- [x] 1.1 Hold each declared repository path to content at `HEAD` in reference closure. Done when
      the closure test fails first and then passes, a mutation that drops the check fails it, and
      the real tree reports `semantic_declaration_missing:path:tools/ci/scripts/**:.ethos/rules.toml`.
- [x] 1.2 Match a reference to an emptied directory as a consumer of its retired files, in closure
      and in deletion admission. Done when both tests fail first and then pass, and a mutation of
      each rule fails its test.
- [x] 1.3 Report every tracked README outside `docs/` that is its directory's only file. Done when
      the docs health test fails first and then passes, a mutation fails it, and the real tree
      reports `docs_readme_without_children:system/projections/README.md`.
- [x] 1.4 Refuse unknown keys in the surfaces contract schema. Done when the contract test fails
      first and then passes, a mutation fails it, and the real tree reports the unread `projection`
      table.
- [x] 1.5 Report each format policy root that admits no tracked file of its format. Done when the
      format selection test fails first and then passes, a mutation fails it, and the real tree
      reports its five dead roots.

## 2. Instances

- [x] 2.1 Remove every dead carrier the checks report, and the audit's unread or unconsumed
      carriers. Done when closure, system contracts, docs health and format selection report
      nothing on the real tree, and no tracked file names a removed path outside archived history.

## 3. Specification and verification

- [x] 3.1 Add the `repository-governance` requirement. Done when strict validation and the
      cumulative archive simulation pass.
- [ ] 3.2 Run the gates and the affected test suites. Done when every gate passes and every
      affected suite passes at the lane head.
