# Tasks

## 1. Resolver

- [x] 1.1 Replace `product_source` with the distribution fact in `adapters/repo/gate_policy.py` and
      remove it from `repository/policy/gates.py` and `repository/policy/quality/gate_composition.py`.
      Done when the symmetry regression (`tests/unit/repository/policy/test_obligation_symmetry.py`)
      compiles equal gates and floor fields across profile id, registry path, location and history,
      and a tree that declares the running distribution binds its own shared data.
      (`unit-architecture` passed at `4f38032de`.)
- [x] 1.2 Accept a captured dependency audit by the content of its product policy in
      `adapters/repo/dependency_acceptance.py`. Done when the acceptance regressions pass for the
      subject's own projection, the judging product's projection and a changed policy
      (`tests/unit/ci/dependency_audit/test_acceptance.py`).
      (`unit-architecture` passed at `4f38032de`.)
- [x] 1.3 Pass the declared import-sorting values to the shared static floor
      (`adapters/gates/python_target.py`, `adapters/gates/python_quality.py`). Done when declared
      `force-single-line` imports pass and a violating block still reports `I001`.
      (`code-static` and `unit-architecture` passed at `4f38032de`.)

## 2. Registries And Evidence

- [x] 2.1 Keep the eight shared entries and `skills`, which the starter rules require, in the form
      every repository runs, in `system/gates.toml`;
      move ETHOS's other gates to `system/repository-gates.toml` and name it in `.ethos/profile.toml`.
      Done when composition supplies the shared floors to ETHOS and the registry tests read the
      registry the profile names.
      (At `4f38032de` the plan ran the composed floors and `unit-architecture` passed.)
- [x] 2.2 Make `unit-architecture` the behavior verifier, add `code-static`, and declare the tooling
      role for `tools/**` and `noxfile.py` in `.gitattributes`. Done when both gates run in the lane
      and `quality_obligation_gaps` is empty for ETHOS's subjects.
      (At `4f38032de` both gates passed and the run reported no quality obligation gap.)
- [x] 2.3 Write the tests session's native outputs under the selected directory
      (`tools/ci/sessions.py`, `tools/ci/python_test_gate.py`). Done when the gate copies this
      attempt's JUnit and Cobertura there (`tests/architecture/test_python_test_gate.py`).
      (`unit-architecture` passed at `4f38032de`.)
- [x] 2.4 Run every product JavaScript module and the npm launcher under the `javascript_tests`
      session's c8, with JUnit and lcov in the selected directory
      (`tests/architecture/product-helpers.test.mjs`, `tests/architecture/npm-package.test.mjs`).
      Done when the session's lcov executes every JavaScript subject and
      `test_javascript_gate_executes_package_behavior` passes.
      (`javascript-tests` and `unit-architecture` passed at `4f38032de`.)

## 3. Contract Texts

- [x] 3.1 Restate the quality and repository-paradigm requirements. Done when strict validation
      passes and the simulated archive leaves every spec valid.
      (`openspec` passed at `4f38032de`; the simulated archive validated every spec.)
- [x] 3.2 Amend the PDC, add DR-0017 and update the documents that restate the old rule. Done when
      `docs-registry`, `markdown-links`, `markdown-lint` and `prose` pass.
      (The four gates passed at `4f38032de`.)
- [x] 3.3 Record the change under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown-lint` and
      `prose` pass.
      (Both gates passed at `4f38032de`.)

## Workflow follow-up

- Rebase onto the accepted `dev` after the `0.2.0-alpha.18` release lands, keeping
  `stable-check-names`' edit of `tests/architecture/test_ci_provider_projections.py`.
- Before the proof, compile `resolve_proof_policies` on the archived head with the installed hook
  runtime and the lane runtime, and compare digests and nodes for `full` and `default`.
- Archive, prove once, land, close out, reinstall the hook from the landed head, and publish `dev`
  to both peers.
