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
- [x] 2.8 Let the native static gate admit an explicitly declared, product-validated execution environment for adopter code that runs in a browser callback, such as `page.evaluate`, without reading candidate ESLint configuration. Today ethos-introduction-film cannot switch runtime: ESLint reports `no-undef` for `window` at `src/motion/render.mjs:347` and `:349`, and render receipts bind that file's bytes. Done when the film's full proof passes under the switched runtime with `render.mjs` unchanged: film Attestation `7c19f1a3` at `4ed2723`.
- [x] 2.9 Run a uv-only project's native behavior tests on an interpreter its `requires-python` admits, instead of always pinning the runtime interpreter; focused tests cover an admitted and an excluded runtime interpreter.
- [x] 2.10 Confirm where coverage thresholds come from: the JavaScript behavior gate passes the adopter's own c8 configuration (`.config/checks/c8/.c8rc.json`) through, requires every behavior subject to be selected, and the Python gate sets no threshold of its own. No product change; an adopter declares its threshold, and c8's 90% line default applies only when it declares none.
- [x] 2.11 Report, for a repository that declares release tags, a version source other than `VERSION`, a tag pattern other than `v*` and a changelog without `## [Unreleased]` or with unbracketed version headings; focused tests cover each case and a repository that does not release.
- [x] 2.12 Read a `.ethos/workspace.toml` without a `branch_roles` table as the standard roles in the strict branch-role reader, as the paradigm report does, so accepted closeout, publication and ref admission no longer reject it; focused tests cover the reader, closeout and ref admission.
- [x] 2.13 Report a document under the profile docs root that does not begin with plain YAML front matter, naming the comment wrapper to remove, and a decision record outside an immutable root not named `dr-NNNN-<topic>.md`, naming its canonical name; focused tests cover both scenarios, a declared docs root and an archived record.
- [x] 2.14 Hold the commit subject grammar in the paradigm contract and apply it, restricted to a declared `scopes` list, when `[commit_policy]` declares no `subject_pattern`; focused tests cover the breaking marker, declared scopes and invalid scope lists.
- [ ] 2.15 Report a `subject_pattern` declared in `[commit_policy]` as a restated commit grammar, once the installed runtime carries 2.14; ETHOS removes its own pattern in the same lane (3.4).
- [ ] 2.16 Retire the docs registry's comment-wrapped metadata reader for documents under the docs root once no adopter tracks such a document; docs health tests cover plain front matter only.

## 3. ETHOS conformance

- [x] 3.1 Move ETHOS tool configuration to tool-named owners under `.config/checks/`, remove the root `ruff.toml` and `.gitleaks.toml` pointers and the `[tool.pytest.ini_options]` table, and bind every consumer explicitly; the paradigm report shows no configuration gap.
- [ ] 3.2 Make the codespell and vulture configuration effective and fail on a missing configuration; a focused test proves each tool reads its declared file.
- [x] 3.3 Bind Prettier for Markdown and YAML, taplo for TOML and Ruff format for Python with the common settings, then format the tracked carriers; a second `check` pass is clean and the paradigm reports no formatter gap. Exposing the verbs as toolchain-owner tasks belongs to 3.5.
- [ ] 3.7 Decide with the OpenSpec artifact owner whether official `openspec/**` Markdown gets a formatter. Today ETHOS declares it official-owner-only, so Prettier excludes it and markdownlint alone checks it; formatting it adds a blank line after every heading and would rewrite glob text such as `operation-intent-*` as emphasis.
- [ ] 3.4 Add `.editorconfig`, rename snake_case repository-authored files such as `rules/module_layout.md` with their references, and adopt the common commit grammar in `.ethos/workspace.toml`; the paradigm report passes on ETHOS.
- [ ] 3.5 Replace ETHOS's repository-owned shell scripts (`bootstrap-python.sh`, `run-head-bound-proof.sh`, `run-secrets-scan.sh` and `with-python-runtime.sh`) and inline CI shell programs with native commands and mise tasks in the CI model and gate catalog, keeping only the generated `mise-install.sh`; the Linux, macOS and Windows jobs run the same tasks and the paradigm report shows no orchestration gap.
- [ ] 3.6 Run the full repository proof on the conforming tree; every required gate passes at the exact head.

## 4. Repair

- [x] 4.1 Add `ethos lane repair-paradigm`: it previews by default, applies only in a Work Lane after exact-path prewrite admission, and plans nothing on a repaired tree; it derives each repair from the gap's obligation and the carrier's current text and reports gaps that need judgment. Focused tests cover preview, apply, refused admission, repetition and a report-only gap. `tests/unit/cli/test_lane_paradigm_repair.py` covers the command; the repaired tree plans no edit in `tests/unit/repository/test_paradigm_repair.py`.
- [x] 4.2 Repair text normalization, formatter bindings and settings, comment-wrapped front matter and a peer's `git_remote`, naming the remote rename as the next action; focused tests cover each repair. An unreadable carrier, a setting whose rewrite would not parse and a front matter without its complete wrapper stay report-only; the three new modules have full line and branch coverage.
- [ ] 4.3 Repair branch-role name fields and a restated commit grammar after 2.15 lands, under the gap formats it defines; focused tests cover each repair.

## Workflow follow-up

- Each adopter migrates through its own Change and switches runtime in the same batch. A repository without foreign Work Lanes or other blockers goes first; otherwise the order follows dependencies and current lane state. The adopters are the proxy, aigw-cli, data-department-work-guidelines, architecture-publisher, web-ingestion-benchmark, the two films and architecture-publications.
- The greenfield-formation Change consumes the paradigm contract when it composes a new repository's foundation.
- The alphasim and di-effect families migrate in their own later Changes; those Changes replace their local size thresholds, di-effect's 500, 800 and 1200-line values and alphasim's 800-line test value, with the paradigm's 512 ceilings.
