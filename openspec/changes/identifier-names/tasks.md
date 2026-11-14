# Tasks

## 1. Identifier sources

- [ ] 1.1 Declare `identifier_sources` in the profile model. Done when a profile with a source row
      of `manifests`, `keys` and `values` is valid and a row with an unknown field or reading is
      refused.
- [ ] 1.2 Read the evidence and admit evidenced names in the paradigm report. Done when the report
      tests show an admitted directory, an admitted file stem, a dotted part and a path segment,
      each listed under `name_admissions` with its manifest, and a name outside the set still
      refused; each test failed before the change.
- [ ] 1.3 Report a declaration without evidence. Done when a glob that matches no tracked file, a
      key that no matched manifest carries and an unparsable manifest each yield
      `repository_paradigm_identifier_source`, and the names they would evidence stay reported.
- [ ] 1.4 Honour the evidence in prewrite admission. Done when a new file whose stem a tracked
      manifest repeats is admitted, the same file is refused while the manifest is untracked, and
      the pinned decision counts of `check_write_paths` and `_check_path` are unchanged.
- [ ] 1.5 Document the key in `docs/architecture/adoption-profiles.md` and add the `CHANGELOG.md`
      line with its rollback sentence. Done when Prettier passes on both files and the Change
      validates with `openspec validate identifier-names --strict`.

## 2. Lane and owner acceptance

- [ ] 2.1 Re-measure the three source budgets on the lane head and register
      `repository_paradigm_identifier_source` when `gap-codes` regenerates its rows. Done when the
      gap registry test passes on the lane head.
- [ ] 2.2 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head.
- [ ] 2.3 After the release that carries this Change is bound, the measured repository declares
      its sources. Done when its audit lists the admissions and reports no authored-name gap for
      an evidenced name.
