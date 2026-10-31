# Tasks

## 1. Registry and measure

- [ ] 1.1 Add the `[[language]]` registry and the class keys `code_effective_lines` and
      `document_nonblank_lines` to `src/ethos/contracts/paradigm/paradigm.toml` and its model, and
      remove `[names] module_suffixes`. Done when `tests/unit/contracts/test_repository_paradigm.py`
      asserts the rows of design decision 2, both defaults of 500, the bound of 1000, and that every
      named lexer resolves in the locked Pygments.
- [ ] 1.2 Add the lexer measure beside the Python measure in `src/ethos/measure.py`. Done when a
      test counts Rust doc comments and comments as excluded and attributes as code, a JavaScript
      block comment as excluded, a shebang as code, and a lexer error token as code.
- [ ] 1.3 Declare Pygments as a runtime dependency in `pyproject.toml` and relock. Done when
      `uv lock --check` passes and the dependency hygiene check accepts the new requirement.

## 2. Obligations

- [ ] 2.1 Resolve the class keys in `src/ethos/repository/paradigm/size.py` and report each retired
      key with its rename. Done when `tests/unit/repository/test_paradigm_report.py` covers every
      row of the size law with `code_effective_lines` and both retired keys.
- [ ] 2.2 Measure every registered code file that is not received as the `code-size` obligation.
      Done when the report tests flag a Go, a Rust and a JavaScript file above the ceiling, pass a
      generated one, pass TOML and YAML of any length, and report an unreadable file.
- [ ] 2.3 Keep module names for the registry languages with `module_names` in
      `src/ethos/repository/paradigm/names.py`. Done when
      `tests/unit/repository/test_paradigm_names.py` admits a snake_case Rust module and its
      directory.
- [ ] 2.4 Judge current documents against `document_nonblank_lines` in docs health. Done when
      `tests/unit/governance/validation/test_markdown_length.py` passes with the class key.

## 3. Documentation and verification

- [ ] 3.1 Describe the code ceiling in `rules/module-layout.md` and record the change in
      `CHANGELOG.md` under Unreleased. Done when the prose and docs gates pass.
- [ ] 3.2 Run every test module that imports a changed module. Done when they pass.
- [ ] 3.3 Run the paradigm report over ETHOS's tree with the candidate contract. Done when it
      reports no code size gap.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out and publish `dev` to
  GitHub only. Build the GitLab supply image from that `dev`, bind it in a binding Change, and
  publish `dev` to both peers.
- After the release that carries it, send each affected repository's file list to the session that
  owns it.
