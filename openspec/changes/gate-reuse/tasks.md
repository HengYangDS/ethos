# Tasks

This is the first slice: keys, the record and the comparison. No task lets a proof skip a gate.

## 1. Statements and the key

- [ ] 1.1 Add the packaged table `src/ethos/contracts/gate-inputs.toml`: the path patterns of the
      nine stated providers and the list of open providers. Done when a test loads it, every name
      in it is an ID of the provider catalog, and no provider is both stated and open.
- [ ] 1.2 Add `src/ethos/adapters/gates/input_key.py` with the statement of a gate: stated,
      whole tree or open. Done when one parametrized test gives the kind for a stated provider, a
      provider outside the table, a command gate, an open provider and a gate that joins a
      stated provider with an open one.
- [ ] 1.3 Compute the key from one listing of the commit's tree: each selected path with its mode
      and object ID, the gate's execution identity, its bound sources and the named inputs. Done
      when tests show the key unchanged by a change to an unselected path and changed by each of:
      a selected path's content, its mode, its removal, the gate's identity, a bound source and
      each named input.
- [ ] 1.4 Read the named inputs once for a run: the running product, the interpreter and
      platform, Git's version, the attribute classification of the committed paths and the names
      of the entries that Git ignores. Done when a test with a local attributes entry for one
      committed document, and a test with a new ignored directory at the root, each get another
      key for `docs-registry`, and a test that sets a marker variable finds neither its name nor
      its value in a key's material.
- [ ] 1.5 Where the running product was built from the proved tree itself, add the committed
      files its wheel is built from to every statement. Done when a test on the product's own
      tree shows a change under `src/ethos/` changing the key of `docs-registry`, and leaving it
      under another running build.
- [ ] 1.6 Hold in the result's data and in the record the count of effective lines, not blank
      and not a comment, of the Git directory's local attributes file, found through Git's own
      path for it; never a pattern. Done when a test of a repository with one such line reports
      1, and without the file 0.

## 2. The record and the comparison

- [ ] 2.1 Write one content-addressed record for a run under `gate-results` in the Git-common
      store: the head, the tree, the named inputs, a digest of the names of the launch
      environment and one row for each gate that executed. Done when a test reads the written
      file back, finds its name equal to the digest of its bytes, finds identical bytes adopting
      the same file, finds no name or value of the environment in it, and finds no row for a
      gate that an unmet prerequisite held.
- [ ] 2.2 Read the earlier results by gate and key. Done when a test with one unparsable file,
      one file of another schema and one valid file returns the valid rows alone and raises
      nothing.
- [ ] 2.3 Compare a decided verdict with the earlier decided results of its key. Done when one
      parametrized test covers agreement, a mismatch in each direction, an unknown result on
      either side, an earlier result of the same tree and one of another tree.
- [ ] 2.4 Give the record a kind in `src/ethos/adapters/store/retention/kinds.py` under the
      existing record floor, with its batch of the apply. Done when the retirement's tests
      classify a written record as owned and a file of another form in the same directory as not
      owned, and an apply deletes a planned record of the kind.

## 3. The proof run

- [ ] 3.1 After the gates of an executed governed proof, and after the source still equals the
      commit, compute the keys, compare, write the record and add the record's name and the
      count of comparisons by state to the result's data, with each mismatch as a note of the
      result and of no check. Done when a test of two executed proofs of one tree shows the
      second counting an agreeing comparison for each gate, with the verdict and required gaps of
      the first, and a test with a planted earlier block shows a note for each gate, an issued
      Attestation and an artifact that names no key and no note. An artifact's digest differs
      between two runs by its timings alone.
- [ ] 3.2 Do the same for a host observation of an expected head and for a readiness run. Done
      when a test shows a readiness run's record compared by a later host observation and by a
      later full proof of the same key.
- [ ] 3.3 Keep a store that is missing, unreadable or refuses a write from changing a proof.
      Done when a test with a store that refuses the record's directory passes the proof and
      the result names the record as unavailable.
- [ ] 3.4 Record nothing for a run whose source changed while its gates ran. Done when a test
      that edits a tracked file during a gate finds no record written.
- [ ] 3.5 Pin that no result of the record is ever passed as settled. Done when a test of the
      product's source finds `settled=` passed only from a readiness result of the same call, in
      the two existing callers.

## 4. Opened files

- [ ] 4.1 While a provider with a statement runs, record each committed file that its process
      opens outside the statement, attributed by the calling context, the product's own files
      and the prepared environment excepted. Done when a test with a provider stub that opens
      one stated and one unstated file finds the unstated file alone in the record, and a test
      with two stubs on two threads finds each file under its own gate.
- [ ] 4.2 Run the nine stated providers on the product's own tree in one bounded test for each
      and require no opened file outside its statement. Done when the nine cases pass, one
      provider a case.

## 5. Documents

- [ ] 5.1 Describe the key, the three statement kinds, the record and the note in
      `docs/architecture/gate-runner.md`, and the result's new fields in
      `docs/reference/command-plane.md`. Done when both pass Prettier, the prose gate and the
      documentation registry, and `tests/unit/repository/test_context.py` and
      `tests/unit/adapters/gates/test_markdown_links.py` pass.
- [ ] 5.2 Name the record's kind and its floor in `docs/architecture/local-state.md`, which
      describes the record retirement, and add one changelog bullet that says no gate is
      skipped. Done when both pass the same checks.

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
