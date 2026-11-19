# Tasks

This is the first slice: keys, the record and the comparison. No task lets a proof skip a gate.

## 1. Statements and the key

- [x] 1.1 Add the packaged table `src/ethos/contracts/gate-inputs.toml`: the path patterns of the
      nine stated providers and the list of open providers. Done when a test loads it, every name
      in it is an ID of the provider catalog, and no provider is both stated and open.
      (At `20cd42dfb` `test_the_packaged_table_names_catalog_providers_and_none_twice` passes: nine
      stated and seven open providers.)
- [x] 1.2 Add `src/ethos/adapters/gates/input_key.py` with the statement of a gate: stated,
      whole tree or open. Done when one parametrized test gives the kind for a stated provider, a
      provider outside the table, a command gate, an open provider and a gate that joins a
      stated provider with an open one.
      (At `20cd42dfb` `test_a_gate_is_stated_keyed_by_the_whole_tree_or_open` passes its 6 cases.)
- [x] 1.3 Compute the key from one listing of the commit's tree: each selected path with its mode
      and object ID, the gate's execution identity, its bound sources and the named inputs. Done
      when tests show the key unchanged by a change to an unselected path and changed by each of:
      a selected path's content, its mode, its removal, the gate's identity, a bound source and
      each named input.
      (At `20cd42dfb` `test_the_key_follows_the_gate_its_selected_paths_and_each_named_input` passes
      its 14 cases.)
- [x] 1.4 Read the named inputs once for a run: the running product, the interpreter and
      platform, Git's version, the attribute classification of the committed paths and the names
      of the entries that Git ignores. Done when a test with a local attributes entry for one
      committed document, and a test with a new ignored directory at the root, each get another
      key for `docs-registry`, and a test that sets a marker variable finds neither its name nor
      its value in a key's material.
      (At `20cd42dfb` `test_local_git_state_is_a_named_input_and_no_environment_value_is` passes.)
- [x] 1.5 Where the running product was built from the proved tree itself, add the committed
      files its wheel is built from to every statement. Done when a test on the product's own
      tree shows a change under `src/ethos/` changing the key of `docs-registry`, and leaving it
      under another running build.
      (At `20cd42dfb`
      `test_the_product_tree_states_its_source_and_carried_files_in_place_of_a_build` passes.)
- [x] 1.6 Hold in the result's data and in the record the count of effective lines, not blank
      and not a comment, of the Git directory's local attributes file, found through Git's own
      path for it; never a pattern. Done when a test of a repository with one such line reports
      1, and without the file 0.
      (At `20cd42dfb` the test of task 1.4 reads 0, 0 and 1 for three runs, and the test of a held
      gate reads 0 from the result's data.)

## 2. The record and the comparison

- [x] 2.1 Write one content-addressed record for a run under `gate-results` in the Git-common
      store: the head, the tree, the named inputs, a digest of the names of the launch
      environment and one row for each gate that executed. Done when a test reads the written
      file back, finds its name equal to the digest of its bytes, finds identical bytes adopting
      the same file, finds no name or value of the environment in it, and finds no row for a
      gate that an unmet prerequisite held.
      (At `20cd42dfb` `test_a_run_is_one_content_addressed_record_and_only_a_parsed_one_is_read` and
      `test_a_held_gate_has_no_row_and_the_record_holds_no_environment_name_or_value` pass.)
- [x] 2.2 Read the earlier results by gate and key. Done when a test with one unparsable file,
      one file of another schema and one valid file returns the valid rows alone and raises
      nothing.
      (At `20cd42dfb` the first test of task 2.1 covers the three files.)
- [x] 2.3 Compare a decided verdict with the earlier decided results of its key. Done when one
      parametrized test covers agreement, a mismatch in each direction, an unknown result on
      either side, an earlier result of the same tree and one of another tree.
      (At `20cd42dfb` `test_a_decided_verdict_is_compared_with_the_decided_results_of_its_key`
      passes its 7 cases.)
- [x] 2.4 Give the record a kind in `src/ethos/adapters/store/retention/kinds.py` under the
      existing record floor, with its batch of the apply. Done when the retirement's tests
      classify a written record as owned and a file of another form in the same directory as not
      owned, and an apply deletes a planned record of the kind.
      (At `20cd42dfb` the retention modules pass, 29 and 3 cases, under Python 3.12, 3.13 and 3.14.)

## 3. The proof run

- [x] 3.1 After the gates of an executed governed proof, and after the source still equals the
      commit, compute the keys, compare, write the record and add the record's name and the
      count of comparisons by state to the result's data, with each mismatch as a note of the
      result and of no check. Done when a test of two executed proofs of one tree shows the
      second counting an agreeing comparison for each gate, with the verdict and required gaps of
      the first, and a test with a planted earlier block shows a note for each gate, an issued
      Attestation and an artifact that names no key and no note. An artifact's digest differs
      between two runs by its timings alone.
      (At `20cd42dfb` `test_each_exact_source_run_is_recorded_and_compared_by_the_next` passes: four
      runs count none, agree, agree and mismatch, and the artifact's text holds no key and no note.
      No test compares the digests of two artifacts.)
- [x] 3.2 Do the same for a host observation of an expected head and for a readiness run. Done
      when a test shows a readiness run's record compared by a later host observation and by a
      later full proof of the same key.
      (The same test runs a readiness run, a host observation and a full proof in that order; each
      later one agrees with the record before it.)
- [x] 3.3 Keep a store that is missing, unreadable or refuses a write from changing a proof.
      Done when a test with a store that refuses the record's directory passes the proof and
      the result names the record as unavailable.
      (At `20cd42dfb` `test_a_store_that_refuses_the_record_changes_no_proof` passes.)
- [x] 3.4 Record nothing for a run whose source changed while its gates ran. Done when a test
      that edits a tracked file during a gate finds no record written.
      (At `20cd42dfb` `test_a_run_whose_source_changed_under_its_gates_records_nothing` passes on
      both planes; it now asserts that the gate ran and that the first gap is
      `proof_execution_source_changed`. With the host observation changed to keep such a run, in a
      disposable clone, its host case fails. A governed run of a tree edited before the run ends as
      `proof_execution_source_mismatch` with no record, in a test of its own.)
- [x] 3.5 Pin that no result of the record is ever passed as settled. Done when a test of the
      product's source finds `settled=` passed only from a readiness result of the same call, in
      the two existing callers.
      (At `20cd42dfb` `test_only_a_run_s_own_readiness_results_stand_for_a_gate` passes.)

## 4. Opened files

- [x] 4.1 While a provider with a statement runs, record each committed file that its process
      opens outside the statement, attributed by the calling context, the product's own files
      and the prepared environment excepted. Done when a test with a provider stub that opens
      one stated and one unstated file finds the unstated file alone in the record, and a test
      with two stubs on two threads finds each file under its own gate.
      (At `20cd42dfb` `test_an_open_belongs_to_the_stated_provider_whose_context_made_it` and
      `test_an_observation_records_what_its_stated_provider_opened` pass. A run that is not kept
      drops its root's names; with that line removed in a disposable clone the first test fails.)
- [x] 4.2 Run the nine stated providers on the product's own tree in one bounded test for each
      and require no opened file outside its statement. Done when the nine cases pass, one
      provider a case.
      (At `20cd42dfb` `test_no_stated_provider_opens_a_committed_file_outside_its_statement` passes
      its 9 cases.)

## 5. Documents

- [x] 5.1 Describe the key, the three statement kinds, the record and the note in
      `docs/architecture/gate-runner.md`, and the result's new fields in
      `docs/reference/command-plane.md`. Done when both pass Prettier, the prose gate and the
      documentation registry, and `tests/unit/repository/test_context.py` and
      `tests/unit/adapters/gates/test_markdown_links.py` pass.
      (At `20cd42dfb`: Markdown lint and the prose gate pass on the three pages and the changelog,
      and both refuse a control; the documentation registry reports no gap; 22 local links resolve;
      the context module passes 18 cases and the links module 1.)
- [x] 5.2 Name the record's kind and its floor in `docs/architecture/local-state.md`, which
      describes the record retirement, and add one changelog bullet that says no gate is
      skipped. Done when both pass the same checks.
      (At `20cd42dfb` the page names the kind and its floor, and the changelog bullet says that no
      gate is skipped; the checks of task 5.1 cover both.)

## 6. Lane, hosted run and owner

- [ ] 6.1 Run `tests/unit/gates`, `tests/unit/adapters/gates`, the importers of the changed
      modules and the architecture guards of the preparation contract under a host ticket. Done
      when each result line is in the lane's record.
- [ ] 6.2 Run two full proofs of one head in the lane and read the second result. Done when it
      counts 34 comparisons, the time between the last gate's end and the result is under one
      second more than in the first, the record directory holds two files, and each record's
      named inputs give `tree` for the running product.
- [ ] 6.3 Read a hosted run of the head on both forges. Done when each passes and its result
      names the record as unavailable or as holding no earlier result.
- [ ] 6.4 Owner: set the arming threshold for `gate-reuse-arming`. Done when the cut's page of
      0.2.0-beta.14 names the counts and the gates that may arm first.
