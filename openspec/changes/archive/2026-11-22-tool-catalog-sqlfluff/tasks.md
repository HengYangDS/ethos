# Tasks

## 1. The row, the repair text and the reference

- [x] 1.1 Add the `sqlfluff` row with its carrier to the packaged paradigm declaration. Done when
      the paradigm report passes a conforming tree that holds `.config/checks/sqlfluff/.sqlfluff`,
      still refuses `config.ini` beside it with the configuration-carrier gap, and
      `native_carrier(".sqlfluff")` returns the carrier. (At `684d73f2b`: the report passes the
      conforming tree with the carrier; `config.ini`, alone or beside the carrier, keeps the
      configuration-carrier gap; a carrier elsewhere under the configuration root is sent to the
      catalogued one; `native_carrier` returns the carrier. The report's module, 80 cases, and the
      gate module, 42 cases, pass.)
- [x] 1.2 Name the declaration of an identifier source in the authored-name gap's repair. Done when
      the gap's next action names the rename, the `linguist-*` marks and `identifier_sources` in
      `.ethos/profile.toml`, and the cases of its test pass. (At `684d73f2b` the gap's next action
      names the rename, the `linguist-*` marks, and the manifest with the key whose value repeats
      the name under `identifier_sources`; the module's 56 cases pass.)
- [x] 1.3 State in the configuration reference the sqlfluff carrier, its binding flags and how
      sqlfluff, Ruff and coverage.py resolve the relative paths of an explicit configuration file,
      and take that statement out of the draft `configuration-reference-gaps`. Done when Prettier
      accepts the reference and the docs registry reports no gap. (At `684d73f2b`: Prettier accepted
      the reference at its commits, and the static pre-check, which runs the documentation registry
      audit, passed on the head's tree `b5aa30c67`. The draft `configuration-reference-gaps` no
      longer names the statement.)

## 2. Lane only

- [x] 2.1 Review the range of 1.1 and 1.2 before the proof. Done when the review's record is
      complete and each comment has its triage. (Seven review records cover `eee24a887` to
      `684d73f2b`, each complete with its triage: 6, 4, 2, 2, 1, 3 and 2 comments. Eighteen were
      answered by a repair and two are accepted as stated residue; none concerns product code after
      the first review.)
- [x] 2.2 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Full pre-check and readiness ran as ticket r4c4 at acf0b50ef (queued 11:34:13, admitted
      11:54:09, released 12:14:26): precheck passed, 0 findings, stamp for tree
      018f0d614ee7db2af1343c7d9acbbdd6c67ddcd3; readiness exit=0, 28 gates passing, 6 not run, 0
      failing.
