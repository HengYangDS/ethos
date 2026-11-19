# Tasks

## 1. The attempt's scratch root

- [x] 1.1 Make one scratch root for a run of gates when it is first asked for, mark it with the
      owner record where the run declares an actor and holds or has joined a host ticket, and
      remove it when the run ends. Done when a test finds the root outside the lane during the
      gates, the mark in it, and no root after the run.
      (At `c2270d5d9` `test_the_commands_of_one_attempt_share_a_marked_scratch_outside_the_lane`
      passes, and `test_the_scratch_of_a_failing_gate_ends_with_its_runner` shows the same end after
      a gate that fails (the lead's review).)
- [ ] 1.2 Give each of the six scratch makers under `src/ethos/adapters/gates` the attempt's root
      as its parent when it runs in a proof, and the temporary root otherwise. Done when one
      parametrized test over the six finds each directory inside the root during an attempt and
      under the temporary root outside one, and was seen failing first.
- [ ] 1.3 Keep the access-time renewal and the owner mark of the behavior probe's directory as
      they are. Done when the existing tests of both pass without an edit.

## 2. The placeholder

- [x] 2.1 Replace `{scratch}` in a declared command's arguments at launch with one directory
      inside the run's root, shared by the run's commands; keep the placeholder in the gate's
      execution identity, and admit a gate's native evidence with the arguments of its launch.
      Done when a fixture command that writes a file to `{scratch}` leaves it inside the root and
      nothing in the lane, a second command reads it, and two attempts of one gate have equal
      identities.
      (At `c2270d5d9` the first test of task 1.1,
      `test_two_attempts_of_one_gate_have_equal_identities` and the 2 cases of
      `test_native_evidence_binds_the_scratch_of_its_launch` pass.)
- [x] 2.2 Leave a command that names no placeholder as it is. Done when a test compares the
      arguments, the working directory and the environment names that such a command receives
      with those of a direct launch of the same command, and no scratch is made.
      (At `c2270d5d9` `test_a_command_without_the_placeholder_is_launched_as_before` passes.)
- [x] 2.3 State the placeholder in the gate runner page beside `{python}` and
      `{native_output}`, with the rule that a registry uses it only once every runtime that
      proves the repository reads it. Done when a test validates a command that names it against
      the published gate schema, which needs no edit, and the page passes Prettier and the
      documentation registry.
      (At `c2270d5d9` `test_the_gate_schema_admits_a_command_that_names_the_scratch` passes and the
      page states the placeholder with the rule. The changelog says that a command which already
      held the literal text now receives the directory (the lead's review).)

## 3. The footprint report

- [x] 3.1 Observe the lane before the first gate and after the last: Git's listing of nontracked
      paths collapsed to directories, the files of the evidence and artifact homes by name, size
      and modification time, and the names directly under the work home. Done when a test over a
      fixture lane reads each of the three.
      (At `c2270d5d9` `test_an_observation_reads_the_roots_the_kept_homes_and_the_work_names`
      passes. The listing runs in the product's observation environment (the lead's review).)
- [x] 3.2 Report the difference in the proof result: for each home the files and bytes that
      appeared or changed, and each new nontracked root. Done when a fixture command that writes
      one report under the evidence home is reported with its bytes, and a lane that no gate
      wrote to reports nothing.
      (At `c2270d5d9` `test_the_report_is_what_appeared_or_changed_and_empty_when_nothing_did`
      passes, and a real proof whose gate writes 2,048 bytes under the evidence home reports them,
      in the test of task 3.3.)
- [x] 3.3 Keep the verdict, the exit and the required gaps of a proof whose report is not empty.
      Done when one test compares two attempts that differ only in what a gate left.
      (At `c2270d5d9` `test_two_proofs_that_differ_only_in_what_a_gate_left_decide_the_same` passes
      its 2 cases.)
- [x] 3.4 Keep the result inside its payload bound. Done when a report of many paths keeps the
      counts and bytes of each class of home and moves the paths to the detail.
      (At `c2270d5d9` `test_a_report_of_many_paths_keeps_its_counts_inside_the_payload_bound`
      passes.)

## 4. Documents and checks

- [x] 4.1 State the attempt's root, the placeholder and the report in the proof and gate pages
      and add the changelog bullets. Done when the pages pass Prettier, the documentation
      registry and the tests of carried documents.
      (At `c2270d5d9` the gate runner page, which is canonical for proof execution, states the
      three, and the two bullets are in the changelog. Markdown lint and the prose gate pass and
      refuse a control; the documentation registry reports no gap; 5 local links resolve; the
      context module passes 18 cases and the quality selection module 15.)
- [x] 4.2 List the tests that import a changed module, run them, run the whole-repository guards
      and measure the three budget totals on the patch. Done when the report holds the list, each
      result line and the totals.
      (With the tree of `c2270d5d9`: 3 own modules and 26 importers, 901 cases in 29 modules and 10
      runs, none failed or skipped (kit test log, labels `r11b*`); the 40 architecture test files
      pass, 311 cases and 1 skipped. Budget from `fb521f462`: product 83,917 to 84,078, tests
      110,834 to 111,113, tools 8,908.)

## 5. Lane, hosted and owner tasks

- [ ] 5.1 The owner answers whether every declared command receives the two variables of the
      plan's item 10. Done when the answer is recorded and decision 5 says the same.
- [ ] 5.2 Run one full proof of ETHOS in a lane on the release that carries this Change and read
      its report. Done when the homes that the report names equal the table of writers in the
      design's context, or the difference is recorded.
- [ ] 5.3 Run the tests of tasks 1.1 to 3.2 on Python 3.12 and 3.13 and on the hosted Windows
      leg. Done when each result line is in the lane's record.
- [ ] 5.4 Open the row that moves ETHOS's own sessions and registry to `{scratch}`, for the
      release after the one that reads the placeholder. Done when its Change holds a proposal
      that names the 25 lines of `tools/ci` and the upload steps that keep their paths.
- [ ] 5.5 Give the row that releases a dead owner's scratch the root and the mark of task 1.1 as
      its input. Done when that row's design cites them.
- [ ] 5.6 Read `residue-class` again with decision 6. Done when its design says which roots a
      proof still writes in a lane and that its second slice finds only rows after one.
