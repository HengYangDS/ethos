# Tasks

## 1. The reader

- [ ] 1.1 Move the bounded provider listing from `retirement.py` into `forge.py` as
      `provider_rows`, with a `key` that names the member of an answered object. Done when the
      reviews tests in `test_retirement_reviews.py` and `test_retirement_retention.py` pass
      unchanged.
- [ ] 1.2 `observe_hosted_runs` in `hosted_runs.py` reads one peer's runs of one commit under two
      provider keys. Done when `test_hosted_runs.py` passes for both providers: no run, a running
      run, a passed run, a failed job, a job that is allowed to fail, skipped runs and two runs of
      one commit.
- [ ] 1.3 An answer that is refused, late, absent, unparsable, about another commit, without an
      identity or in an unknown word is `unknown` with its reason and no stderr, and an unresolved
      or unsupported peer runs no provider command. Done when the two `unknown` tests pass.
- [ ] 1.4 A run that passed is one row whose jobs are not read; a run that failed or still runs
      lists only its jobs that did not pass. Done when the reader's table counts one provider
      call for a passed run and one more for each run that failed or still runs.
- [ ] 1.5 Name, for an unknown peer, the query that failed or a step by hand. Done when a failed
      read of a run's jobs names that read, an answer that the reader does not use names no
      query, and a peer whose provider has no reader names its declaration.

## 2. The observation and its command

- [ ] 2.1 `hosted_observation` in `application/publication/hosted.py` reads every CI peer and
      names each peer that did not pass. Done when two peers that disagree stay two facts in
      `test_hosted_observation.py`.
- [ ] 2.2 Register `hosted_run_failed`, `hosted_run_missing`, `hosted_run_running` and
      `hosted_run_unknown` in the gap registry, each with its meaning and repair. Done when
      `tests/architecture/test_gap_registry.py` passes.
- [ ] 2.3 `publish --observe-hosted` selects `publish.hosted.observe`, with the effects `read` and
      `remote-read` and an exit by verdict. Done when the operation catalog test counts 108
      operations and 18 unmatched `publish` assignments, and the root help lists 30.
- [ ] 2.4 The command blocks for a failed run or a missing one, is `unknown` for a running or
      unreadable peer, repeats itself only while a run may conclude, refuses another expected
      head without a provider command, and passes as `no_ci_peer` without a CI peer. Done when
      `test_hosted_observation.py` passes.
- [ ] 2.5 Order the gaps by what decides, count the observed CI peers in the summary, and keep a
      next action for a declaration that cannot be observed. Done when a peer without a run
      beside an unreadable one names the publication as the repair, the summary counts zero
      peers for `no_ci_peer`, and three invalid declarations each block with a next action.

## 3. The landing preview and the release probe

- [ ] 3.1 The candidate preview carries `data.hosted_observation`, an apply carries none, and
      `land.preview` declares `remote-read`. Done when the preview test shows the same verdict and
      required gaps for a head whose runs passed and one whose peers failed or hold no run, two
      provider calls for the clean head, and its entry under 1,024 bytes.
- [ ] 3.2 The probe of the release branch or a release tag carries `data.hosted_observation` of
      its proof head and keeps its verdict and gaps; a probe of another ref reads no forge. Done
      when the release probe test passes for the release branch and the role table holds the
      release branch and a release tag as the only release refs.

## 4. Documents

- [ ] 4.1 The reference's root table and exit sentence, the changelog entry and the spec delta.
      Done when Prettier, the documentation registry and
      `openspec validate hosted-observation --strict` pass.

## 5. Lane, hosted run and owner

- [ ] 5.1 Lane: run the lane's check and the full proof at the committed head. Done when both
      pass.
- [ ] 5.2 Hosted run: with a signed-in CLI, run `ethos publish --observe-hosted --json` once
      against each forge for a head that has a failed run. Done when each peer's runs and the
      failed run's jobs are listed with the states the forge shows, or the reader's keys are
      corrected to the JSON it prints.
- [ ] 5.5 Owner: name the release in which a release ref requires a passing observation, no
      earlier than the release after this one, after the three cases of decision 8 are measured
      on the governed repositories. Done when the decision names a release and a successor Change
      is opened for the refusal, its Breaking entry, its repair and the stored record.
