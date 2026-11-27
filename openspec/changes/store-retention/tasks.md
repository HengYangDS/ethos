# Tasks

## 1. The release of an absent consumer

- [x] 1.1 Read absence in one function of the host retention module: `os.lstat`, where only
      `FileNotFoundError` and `NotADirectoryError` mean absent and any other failure means
      unknown. Done when tests answer absent, absent, present and unknown for a missing path, a
      path below a regular file, an existing path and a path below a directory without search
      permission.
      (At `fb521f462` `test_only_a_missing_entry_is_absence` passes its 3 cases and
      `test_a_place_the_host_cannot_look_at_is_unknown_and_is_never_planned` passes, under Python
      3.12, 3.13 and 3.14.)
- [x] 1.2 Plan the absent consumer records under `install.lock`: for each one the installation,
      the record, the consumer path, the scanned repositories that name the installation and the
      bytes it holds, with one digest over the rows. Done when a preview over a fixture store
      lists exactly the absent records, plans none whose absence is unknown and none while a
      scanned repository's selection cannot be read, and a listing of the installations is equal
      before and after.
      (At `fb521f462` `test_the_preview_names_exactly_the_absent_records_and_changes_nothing` and
      `test_a_scanned_selection_that_cannot_be_read_keeps_the_records_out` pass.)
- [x] 1.3 Apply the plan: refuse a digest that differs, record each scanned repository that names
      an installation, then unlink each planned record whose path is still absent. Done when
      tests show a changed plan unlinking nothing, a moved repository keeping its installation
      through the next cleanup, a path that came back keeping its record, and no installation
      removed by the apply.
      (At `fb521f462` `test_a_changed_plan_releases_nothing`,
      `test_an_applied_plan_releases_the_records_and_removes_no_installation`, which runs the next
      cleanup for a moved repository, and
      `test_a_path_that_came_back_during_the_apply_keeps_its_record` pass.)
- [x] 1.4 Add the switch to the request and to the operation's request fields, and branch on it
      in the application: the summary's counts, the apply as the preview's next step and the
      cleanup of `hook install` as the apply's. Done when the command's tests cover a preview, an
      apply without a plan, an apply without the authorization and an applied release.
      (At `fb521f462` the command's module passes 5 cases: a preview with its applied release, an
      apply without a plan, one without the authorization, a call without the switch, and a release
      that fails in the middle. That last case is the lead's review: the release is blocked and
      still names what it released, and without the repair the case fails in a disposable clone.)
- [x] 1.5 Keep every invocation without the switch as it is. Done when
      `tests/unit/adapters/repo/runtime/materialization/test_legacy_supply.py` and
      `tests/unit/cli/test_hook_supply_retirement.py` pass without an edit.
      (Both modules are unedited at `fb521f462` and pass, 3 cases each.)

## 2. The store report and the budget rows

- [x] 2.1 Report the regular files and their bytes under each top-level name of the Git-common
      store, links not followed, and the time of the read. Done when a fixture store with a link
      and a nested tree reports the expected counts and sizes.
      (At `fb521f462` `test_the_report_counts_regular_files_by_name_and_follows_no_link` and
      `test_a_directory_that_cannot_be_read_is_counted_and_the_rest_is_reported` pass.)
- [x] 2.2 Report the bytes in the verb's owned directories against `retention.status_bytes` in
      the preview's summary, and say so in the row's comment in the paradigm. Done when one test
      gives `within` and `over` for one store under two declared values, and asserts that
      verdict, state, required gaps and next action are equal in both.
      (At `fb521f462` `test_a_row_is_over_only_above_its_budget` passes its 2 cases and
      `test_a_row_that_is_over_changes_nothing_else_in_the_preview` passes. The paradigm's comment
      on the group says that the previews report and that no command refuses for bytes.)
- [x] 2.3 Declare `retention.host_bytes` in the paradigm and report the host store's
      installations against it in the preview of `hook retire-supply`. Done when the parameter's
      tests accept the row and the preview's summary holds it, with and without the switch.
      (At `fb521f462` the row is declared, the parameter module passes 6 cases and
      `test_the_supply_preview_reports_the_host_installations` passes its 2 cases.)

## 3. Documents and derived tables

- [x] 3.1 State the switch, the report and the two rows in the command reference and the
      local-state page. Done when both pass Prettier, the documentation registry and the tests of
      carried documents.
      (At `fb521f462` both pages state the three. Markdown lint and the prose gate pass and refuse a
      control; the documentation registry reports no gap; 18 local links resolve. With the tree of
      `c2270d5d9` the context module passes 18 cases and the quality selection module 15, and the
      architecture tests pass.)
- [x] 3.2 Add the changelog bullets for the release and the report, and move the absent consumer
      out of the known open defects of the entry that ships it. Done when the entry names the
      command that releases one.
      (The two bullets are under Added in the unreleased section at `fb521f462`. The release's
      bullet names the command and says that it closes the known open defect of 0.2.0-beta.11. The
      unreleased entry holds no list of known open defects; the entry of 0.2.0-beta.11 is frozen and
      keeps its line.)
- [ ] 3.3 Run every guard of the catalog: all of `tests/unit/cli` and `tests/architecture`,
      through the host queue. Done when both pass on the final tree.
- [x] 3.4 List the tests that import a changed module and run them, then measure the three
      budget totals on the patch. Done when the report holds the list, each result line and the
      totals.
      (With the tree of `fb521f462`: 4 own modules and 11 importers and readers of the changed
      tables, 298 cases in 15 modules, none failed or skipped (kit test log, labels `r11a*`). Budget
      from `213bbd533`: product 83,705 to 83,917, tests 110,375 to 110,834, tools 8,908.)

## 4. Lane, hosted and owner tasks

- [ ] 4.1 The owner answers where the release lives and which values the two rows take. Done when
      the answers are recorded and the design's decisions 1 and 7 say the same.
- [ ] 4.2 Run the tests of tasks 1.1 to 1.4 and 2.1 on Python 3.12 and 3.13, and on the hosted
      Windows leg. Done when each interpreter's result line is in the lane's record.
- [ ] 4.3 On the releasing host, run the preview with the switch and compare its rows with the
      `absent` list of the cleanup's report. Done when the difference, if any, is explained by
      decision 2. The apply runs only on the owner's authorization.
- [ ] 4.4 Take the 48-hour observation on the frozen beta: three previews of each store, at the
      start, near 24 hours and after 48 hours, with at least one full proof and one lane
      retirement between the first and the last. Done when a session other than the authors' has
      read the three results against decision 9 and the candidate's acceptance cites them.
- [ ] 4.5 Open the row for the kinds that the archived apply design left out, or record its
      deferral with an owner and a review date. Done when one of the two exists.
- [x] 4.6 Name each consumer that the cleanup keeps without reading it. The report lists a
      consumer only when it is absent; one that reads `unknown` (a path below a directory that
      may not be searched, a link that names nothing, a file left at the path) keeps its
      installation and appears under no name. Done when the cleanup's report and the preview of
      the release name such a consumer with the reason it was not read, and a case holds each of
      the three states. Found by the model review of the consumer reader's repair in
      `beta-11-head-move`.
      (The cleanup's report and the release preview list `unread` consumers with their reason:
      `not_a_directory` and `dangling_link` in
      `test_a_consumer_whose_path_is_gone_keeps_its_record_and_installation` and
      `test_the_preview_names_a_record_whose_consumer_it_could_not_read`, `unanswered` in
      `test_a_place_the_host_cannot_look_at_is_unknown_and_is_never_planned`.)
