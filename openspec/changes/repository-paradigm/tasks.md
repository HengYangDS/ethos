## 1. Contract and authority

- [ ] 1.1 Add the packaged repository paradigm contract beside the generated-artifact topology contract, holding the root catalog, configuration groups, tool catalog, binding file set, common OpenSpec rules and commit grammar; a loader test parses it and rejects unknown keys.
- [x] 1.2 Record the decision and its limits in DR-0012 and amend the Product Design Contract, Config Boundary Model and Repository Profile Contract statements that forbid a common repository layout; docs health and link checks pass.

## 2. Evaluation

- [ ] 2.1 Add the paradigm report to the repository audit composition, naming each gap's carrier, obligation and canonical repair; focused tests cover every scenario in `specs/repository-paradigm/spec.md`.
- [ ] 2.2 Refuse non-conforming root, configuration-plane and binding paths in prewrite through the CEL topology rules, naming the canonical path; predicate tests cover each refusal.
- [x] 2.3 Read Gitleaks and Ruff configuration in pre-commit admission from their canonical `.config/checks/` paths and report configuration found elsewhere; hook admission tests cover both cases.
- [ ] 2.4 Make sibling Work Lane worktrees under `<repository>-worktrees/<yyyymmdd>-<slug>/` the default and retire the opt-in; lane start tests cover the default path.

## 3. ETHOS conformance

- [ ] 3.1 Move ETHOS tool configuration to tool-named owners under `.config/checks/`, remove the root `ruff.toml` and `.gitleaks.toml` pointers and the `[tool.pytest.ini_options]` table, and bind every consumer explicitly; the paradigm report shows no configuration gap.
- [ ] 3.2 Make the codespell and vulture configuration effective and fail on a missing configuration; a focused test proves each tool reads its declared file.
- [ ] 3.3 Bind Prettier for Markdown and YAML and taplo for TOML through `fix` and `check` tasks of the mise toolchain owner, then format the tracked carriers; a second `check` pass is clean.
- [ ] 3.4 Add `.editorconfig`, rename snake_case repository-authored files such as `rules/module_layout.md` with their references, and adopt the common commit grammar in `.ethos/workspace.toml`; the paradigm report passes on ETHOS.
- [ ] 3.5 Run the full repository proof on the conforming tree; every required gate passes at the exact head.

## Workflow follow-up

- Each adopter migrates through its own Change and switches runtime in the same batch: the proxy, aigw-cli, data-department-work-guidelines, architecture-publisher, web-ingestion-benchmark, the two films, then architecture-publications.
- The greenfield-formation Change consumes the paradigm contract when it composes a new repository's foundation.
- The alphasim and di-effect families migrate in their own later Changes.
