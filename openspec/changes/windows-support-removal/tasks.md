# Tasks

## 1. The accepted specifications

- [ ] 1.1 Search the specification deltas of every open Change at the lane's base for the 22
      requirement titles and the 32 scenario names of the design's tables. Done when the search
      names none, or each Change it names is re-homed first; the search is repeated before the
      landing.
- [ ] 1.2 Remove the 32 scenarios that the design lists from the accepted specifications, by
      deletions only. Done when a script that compares the accepted specifications at the lane's
      base and head names exactly the listed pairs of requirement title and scenario name, no added
      line and no changed statement, and `openspec validate --specs --strict` passes.
- [ ] 1.3 Put the retired, reworded and added accepted text to the owner with its Chinese meaning:
      the 32 retired scenarios and the 6 that leave with a removed requirement, by name and text;
      the reworded statements and scenarios; the two added requirements; the contract's two
      sentences; the decision record; and by name the two effects that no earlier release reported
      (a pipeline declaration naming `windows` stops compiling; a bind with a Mise pin that keeps
      the Windows rows, as task 5.4 measures it). The four pieces that stay are decided (the owner's
      decision of 2026-11-26). Done when his answer is recorded in the decision record; the lane
      does not land before.
- [ ] 1.4 Have the lane's independent review rerun the comparison of task 1.2 on the retiring commit
      and answer, for each of the 38 scenarios of the design's tables, whether the product still
      does it or which title states it. Done when the design's section "Review of the retirements"
      names the reviewer and the commit and resolves each answer that differs.

## 2. The product

- [ ] 2.1 Remove every Windows branch of `src/ethos` and the code only it reached. Done when
      `rg -i 'windows|win32|os\.name' src/ethos` names only the script-kind detection
      (`repository/paradigm/scripts.py`, `orchestration.py`), the paradigm's `leaving_platforms`
      entry and the noun "windows" in the comment of `adapters/repo/attestation_lifetime.py`, the
      shipped hook declaration still holds both `posix` and `nt` and its reader accepts `nt` as the
      only key beside `posix`, the hook generation digest equals that of 0.2.0-beta.12, and the unit
      tests of the touched modules pass.
- [ ] 2.2 Keep `git_object_trust_anchor_protection_failed` on a refused permission change and remove
      the three gap codes that lost their producer. Done when the trust-anchor tests pass and the
      gap registry's own tests pass.
- [ ] 2.3 Read a retention record that names the platform `windows` and report it. Done when the
      test of a record that names a leaving platform passes: the step stays retained and the audit
      names `repository_paradigm_retained_step_platform` among the gaps that do not block.

## 3. Delivery and CI

- [ ] 3.1 Remove the Windows legs, the dispatch input and the optional and emulated release legs
      from `.config/ci/pipeline.cue`, and regenerate the GitHub workflow. Done when the projection
      check reports nothing but `supply_image_stale` (task 5.1 clears it) and the workflow names no
      Windows runner.
- [ ] 3.2 Give release assembly one list of hosts, and the shared test helper
      `tests/support/release_legs.py` the same one host set. Done when a leg whose runtime is not
      its declared host's is refused with `release_assets_distribution_mismatch` and a missing host
      with `release_assets_platform_missing`.
- [ ] 3.3 Remove the Windows platform records from the Mise lock, declare the Python lock's two
      environments, and remove the constraint `uv<0.13.9` with its comment. Done when
      `uv lock --check` and `mise install --locked` pass, neither lock names Windows, and
      `pyproject.toml` holds no `uv<` constraint.

## 4. Tests and records

- [ ] 4.1 Remove the Windows-only test cases and `tests/support/windows_host.py`, and the Windows
      leg of `tests/support/release_legs.py`; lower the decision-density baseline to the measured
      scores. Done when the whole pre-check passes.
- [ ] 4.2 Carry the reworded and the new requirement texts into the seven delta specifications. Done
      when `openspec validate windows-support-removal --strict` passes and the archive simulation
      validates every accepted specification.
- [ ] 4.3 Reword the contract's two sentences, the guides and the reference, and remove the two
      research passages that steer Windows work. Done when the Markdown gates pass and
      `rg -i windows` over those files names only the decision record's link.
- [ ] 4.4 Add the changelog entry and DR-0038. Done when DR-0038 records the owner's two decisions
      of 2026-11-26 and his answer of task 1.3, each by its date and without his verbatim words, and
      the changelog entry names the step an adopter takes as task 5.4 measured it.
- [ ] 4.5 Close the known-defect entry on a finished queue run (its `fixed_in` filled by the release
      Change), reword and rename the entry on a slot bound to its holder to its remaining reach, and
      add an entry on removed steps that `openspec_spec_obligation_removed` does not see. Done when
      the known-defect entries' own check passes and each of the three entries names this Change.

## 5. Verification

- [ ] 5.1 After the tests and documents are committed, publish the proposal and rebuild the supply
      image on the lane's GitHub proposal ref, then bind its digest and source commit in
      `.config/ci/pipeline.cue`. Done when the projection check reports no `supply_image_stale`.
- [ ] 5.2 Run the whole pre-check and the readiness tier at the lane head, then the full proof; read
      the patch size and the source budget at that head into the design's "Measured". Done when the
      proof is proven at that head and "Measured" names that head.
- [ ] 5.3 Run the hosted qualification on GitHub and the full gate set on GitLab at the head. Done
      when every leg of the three platforms passes on GitHub, GitLab's pipeline passes, and neither
      holds a Windows job.
- [ ] 5.4 With the candidate archives of that run, bind copies of two governed repositories whose
      Mise pin lists the two Windows rows (`architecture-publications` and `ethos-film`): once with
      the rows left in place, once with them removed, and once upgraded by
      `ethos lane repair-paradigm --pin`. Done when what `mise install --locked` and `mise lock` do
      in each case is recorded in the design's "Measured" and the changelog entry states the step an
      adopter takes.
