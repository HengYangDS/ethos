## 1. Contract and authority

- [ ] 1.1 Add the packaged repository paradigm contract beside the generated-artifact topology contract, holding the root catalog, configuration groups, the tool catalog with its official generators, the binding file set, common OpenSpec rules and commit grammar; a loader test parses it and rejects unknown keys.
- [x] 1.2 Record the decision and its limits in DR-0012 and amend the Product Design Contract, Config Boundary Model and Repository Profile Contract statements that forbid a common repository layout; docs health and link checks pass.

## 2. Evaluation

- [ ] 2.1 Add the paradigm report to the repository audit composition, naming each gap's carrier, obligation and canonical repair; focused tests cover every scenario in `specs/repository-paradigm/spec.md`.
- [x] 2.2 Refuse non-conforming new root, configuration-plane and binding paths in prewrite through the report's path obligations, naming the canonical path; prewrite tests cover each refusal and an edit to an existing carrier.
- [x] 2.3 Read Gitleaks and Ruff configuration in pre-commit admission from their canonical `.config/checks/` paths and report the root names that the paradigm tool catalog lists for them, including the retired `.gitleaks.toml` and `ruff.toml`; hook admission tests cover both cases.
- [ ] 2.4 Make sibling Work Lane worktrees under `<repository>-worktrees/<yyyymmdd>-<slug>/` the default and retire the opt-in; lane start tests cover the default path.
- [x] 2.5 Add the 512 Python effective-line and Markdown nonblank-line ceilings to the paradigm contract: the paradigm report measures every tracked Python file and reports a `[quality.code_size]` binding, docs health reads the Markdown ceiling of proof-throughput task 12.4 from the contract, the rules policy retires and the `python-size` gate reports the paradigm measurement; focused tests cover both ceilings, the reported binding and the gate projection.
- [ ] 2.6 Retire the `python-size` gate through an ordinarily landed lane. Today the installed runtime compares a candidate's `system/gates.toml` with its own packaged copy, treats any changed ETHOS registry as an adopter registry and applies the adopter quality floor, so `land` reports `proof_attestation_repository_policy_mismatch`; done when that comparison no longer depends on the installed copy and the gate is removed.
- [x] 2.7 Report each publication peer whose `git_remote` differs from its peer id, naming the rename; focused tests cover a peer-named remote and the implicit `origin`.

## 3. ETHOS conformance

- [x] 3.1 Move ETHOS tool configuration to tool-named owners under `.config/checks/`, remove the root `ruff.toml` and `.gitleaks.toml` pointers and the `[tool.pytest.ini_options]` table, and bind every consumer explicitly; the paradigm report shows no configuration gap.
- [ ] 3.2 Make the codespell and vulture configuration effective and fail on a missing configuration; a focused test proves each tool reads its declared file.
- [x] 3.3 Bind Prettier for Markdown and YAML, taplo for TOML and Ruff format for Python with the common settings, then format the tracked carriers; a second `check` pass is clean and the paradigm reports no formatter gap. Exposing the verbs as toolchain-owner tasks belongs to 3.5.
- [ ] 3.7 Decide with the OpenSpec artifact owner whether official `openspec/**` Markdown gets a formatter. Today ETHOS declares it official-owner-only, so Prettier excludes it and markdownlint alone checks it; formatting it adds a blank line after every heading and would rewrite glob text such as `operation-intent-*` as emphasis.
- [ ] 3.4 Add `.editorconfig`, rename snake_case repository-authored files such as `rules/module_layout.md` with their references, and adopt the common commit grammar in `.ethos/workspace.toml`; the paradigm report passes on ETHOS.
- [ ] 3.5 Replace ETHOS's repository-owned shell scripts (`bootstrap-python.sh`, `run-head-bound-proof.sh`, `run-secrets-scan.sh` and `with-python-runtime.sh`) and inline CI shell programs with native commands and mise tasks in the CI model and gate catalog, keeping only the generated `mise-install.sh`; the Linux, macOS and Windows jobs run the same tasks and the paradigm report shows no orchestration gap.
- [ ] 3.6 Run the full repository proof on the conforming tree; every required gate passes at the exact head.

## Workflow follow-up

- Each adopter migrates through its own Change and switches runtime in the same batch: the proxy, aigw-cli, data-department-work-guidelines, architecture-publisher, web-ingestion-benchmark, the two films, then architecture-publications.
- The greenfield-formation Change consumes the paradigm contract when it composes a new repository's foundation.
- The alphasim and di-effect families migrate in their own later Changes; those Changes replace their local size thresholds, di-effect's 500, 800 and 1200-line values and alphasim's 800-line test value, with the paradigm's 512 ceilings.
