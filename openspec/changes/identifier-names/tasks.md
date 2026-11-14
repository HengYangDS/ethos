# Tasks

## 1. Identifier sources

- [x] 1.1 Declare `identifier_sources` in the profile model. Done when a profile with a source row
      of `manifests`, `keys` and `values` is valid and a row with an unknown field or reading is
      refused.
- [x] 1.2 Read the evidence and admit evidenced names in the paradigm report. Done when the report
      tests show an admitted directory, an admitted file stem, a dotted part and a path segment,
      each listed under `name_admissions` with its manifest, and a name outside the set still
      refused; each test failed before the change.
- [x] 1.3 Report a declaration without evidence. Done when a glob that matches no tracked file, a
      key that no matched manifest carries and an unparsable manifest each yield
      `repository_paradigm_identifier_source`, and the names they would evidence stay reported.
- [x] 1.4 Honour the evidence in prewrite admission. Done when a new file whose stem a tracked
      manifest repeats is admitted, the same file is refused while the manifest is untracked, and
      the pinned decision counts of `check_write_paths` and `_check_path` are unchanged.
- [x] 1.5 Document the key in `docs/architecture/adoption-profiles.md` and add the `CHANGELOG.md`
      line with its rollback sentence. Done when Prettier passes on both files and the Change
      validates with `openspec validate identifier-names --strict`.

## 2. Lane and owner acceptance

- [x] 2.1 Re-measure the three source budgets on the lane head and register
      `repository_paradigm_identifier_source` when `gap-codes` regenerates its rows. Done when the
      gap registry test passes on the lane head; the Change's own commit measures +112.4 product,
      +126.0 tests and 0 tools over the lane base.
- [x] 2.2 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head.
- [x] 2.3 Record the declaration that the measured repository will carry. Done when the probe's
      declaration of six sources admits every name at the measured tip (133 of 133 at `9efd42c67`)
      with no source gap, as the Change's report records in its measured-tree table.

## Workflow follow-up

- after the release that carries identifier-names is bound in the measured repository, its profile
  declares the six `[[identifier_sources]]` rows and its audit lists the admissions with no
  authored-name gap for an evidenced name.
