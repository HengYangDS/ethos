# Tasks

## 1. Failing evidence first

- [x] 1.1 Add a case to `tests/unit/adapters/gates/test_native_inputs.py`: in a governed fixture
      that deletes a tracked Markdown file without staging the deletion, `quality_source_files`
      omits the path and `authored_text_gaps` over the authored inputs reports no
      `authored_text_path_invalid`. Done when it fails at the lane's base. (At the base the deleted
      `docs/gone.md` was listed.)
- [x] 1.2 Add a case to `tests/unit/cli/test_proof_command.py`: a focused proof whose only gaps are
      `quality_obligation_unproven:<axis>` names `ethos prove --execute --json`, and any other
      refused plan keeps "repair the Commitment or repository facts". Done when the first half fails
      at the lane's base. (At the base the next action was the plan repair text.)
- [x] 1.3 Make the explicit-selection case of `tests/unit/adoption/quality/native/test_node.py`
      expect the scope gap to name the selected test file that the runner never entered. Done when
      it fails at the lane's base, whose gap names no file. (At the base the gap was the bare code.)

## 2. One inventory owner and named remedies

- [x] 2.1 Make `quality_source_files` subtract `git ls-files --deleted` and remove the existence
      filter in `native_repository_configuration`. Done when 1.1 and
      `tests/unit/adapters/gates/test_native_inputs.py` pass. (Of 426 cases in the 13 affected
      modules, one source-format case failed once in a four-worker run on a loaded host; it passed
      alone at the base and in the lane, and its module passed twice with four workers.)
- [x] 2.2 Make the proof's next action name the full proof for a focused refusal of unselected axes.
      Done when 1.2 and `tests/unit/cli/test_proof_command.py` pass. (Both modules pass.)
- [x] 2.3 Make the JavaScript test-scope refusal name the files that differ. Done when 1.3 and
      `tests/unit/adoption/quality/native/test_node.py` pass. (The module passes.)

## 3. Specifications and documents

- [x] 3.1 Write the quality and command-plane deltas. Done when strict OpenSpec validation passes.
      (It passes.)
- [ ] 3.2 Add the fix to CHANGELOG's `[Unreleased]`. Done when the documentation gates pass.

## Workflow follow-up

- Archive, prove the archived head once, land, close out and publish to both peers; confirm both
  hosted planes pass.
