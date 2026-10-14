## Context

A read-only inventory on 2026-10-14 covered the thirteen Git repositories that track an ETHOS binding: ETHOS, the OpenAI Responses Proxy, aigw-cli, architecture-publisher, architecture-publications, data-department-work-guidelines, two introduction films, web-ingestion-benchmark, two alphasim clones and two di-effect clones. One di-effect clone tracks no binding, and one alphasim repository is a clone of the other.

Shared by every repository where the concern applies:

- `README.md` and `openspec/config.yaml`;
- `.ethos/profile.toml`;
- `build/` ignored as the generated root;
- Python 3.12 as the compatibility floor;
- a formatter width of 100;
- SSH-signed Conventional Commits wherever a commit policy exists;
- the five lane roles wherever lanes are declared.

Shared by most repositories:

- `AGENTS.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `docs/`, `tools/`, `.config/` and a GitLab pipeline;
- Prettier with preserved prose wrapping;
- taplo;
- numbered decision records.

Each repository encodes the same concerns differently:

- seven `.ethos/` file sets, with gate declarations in three places;
- five commit grammars;
- branch prefixes `proposal/` and `submit/`, `work/` and `task/`, and both `main` and `master`;
- three `.config/` taxonomies (by tool, by concern, by quality kind);
- tool configuration at the root and inside manifests;
- four decision-record namings;
- front matter in YAML or inside HTML comments;
- hand-maintained CI files for two Forges in three repositories.

ETHOS's current documents prevent a common answer:

- The Config Boundary Model says a profile must not make `.config/` layout universal.
- The Repository Profile Contract calls layout an adopter choice.
- The Product Design Contract says each repository retains its domain model, layout and provider shape.

DR-0011 already rejected a cloned documentation tree, because path equality does not prove semantic equivalence and forced empty carriers. This Change keeps that lesson: it standardizes carriers that every repository actually has, never empty structure.

Existing enforcement points:

- The repository audit (`audit_for_root`) is profile-independent and blocks prove, land and publish for every repository.
- Prewrite applies the packaged generated-artifact topology rules to every requested path.
- Pre-commit admission scans secrets and checks staged Python formatting only when root `.gitleaks.toml` and `ruff.toml` exist.
- Each repository's Git common directory selects its ETHOS runtime. Adopters change runtime through `ethos hook install`.

## Goals / Non-Goals

**Goals:**

- One ETHOS-owned paradigm for every governed repository, holding only what the repositories genuinely share.
- Mechanical conformance: every obligation is decidable from tracked paths and declared carriers.
- One blocking verdict with a canonical repair for each gap, evaluated the same way everywhere.
- ETHOS conforms in this Change, so the product proves its own contract.

**Non-Goals:**

- Product or domain structure, test organization, documentation subject layout and provider shape.
- Choosing tools for a repository. The paradigm says where a configured tool's files live, not which tools to adopt.
- Forge-side settings, remote branch protection and hosted runner provisioning.
- Migrating the alphasim and di-effect families now. They were analysed for commonality and stay deferred under the workstation rule.

## Decisions

### 1. Three layers, and what counts as common

The paradigm has three layers:

- the **core**, which every governed repository satisfies;
- **ecosystem modules** for Python, Node and Go, each applied exactly when its manifest exists;
- **repository-owned** structure, which the paradigm does not touch.

An obligation enters the core or a module only when every repository where the concern applies already needs it. Where repositories need the same thing in different encodings, the decision below picks one encoding and gives the reason. Concerns present in a single repository stay with that repository; they enter the paradigm only through a later ETHOS Change that shows they are shared.

### 2. One packaged contract, evaluated at existing enforcement points

The obligations are product data in a packaged contract beside `src/ethos/contracts/artifacts/topology.toml`. The contract holds the root catalog, configuration groups, the tool catalog, the binding file set and the common rules. It is evaluated in three places:

- **Whole tree:** a paradigm report in the repository audit composition. It inherits the audit's blocking behaviour in prove, land and publish.
- **Path level:** prewrite rules in the existing CEL topology vocabulary, so a non-conforming path is refused before it is written.
- **Staged:** pre-commit admission reads Gitleaks and Ruff configuration from their canonical paths.

Alternatives rejected:

- A per-repository paradigm file: it recreates per-repository improvisation.
- A new gate or command: the audit already owns profile-independent governance.
- A documented convention without enforcement: the inventory shows conventions drift without an owner.

### 3. Configuration groups by consuming tool, not by concern

`.config/checks/<owner>/` and `.config/release/<owner>/` are named by the consuming tool, or by a repository check when only repository-owned parameters exist. The Config Boundary Model already separates how a tool runs (its configuration) from why it runs (the profile and gate catalog), and directory names follow the first.

A shared concern vocabulary did emerge (`secrets`, `prose`, `markdown`, `toml` and `links` appear in several repositories), but it fails mechanically:

- Ruff serves lint and format.
- Prettier formats several file types.
- `dependencies` mixes deptry and OSV-Scanner.

A concern vocabulary would need an ETHOS-owned assignment of every tool to a concern, which is an opinion table. A tool catalog maps canonical basenames to tool identifiers, which are facts from each tool's documentation. Concern grouping stays in the profile or a repository responsibility catalog.

The packaged contract holds the complete tool catalog as executable data. The rows below were verified against the locked versions in the fleet and fix the encodings that a migration must get right.

| Tool                                                                                | Canonical carrier                                                                  | Binding and constraint                                                                                                                                             |
| ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| pytest                                                                              | `.config/checks/pytest/pytest.toml`                                                | `-c` together with `--rootdir`. Only the `pytest.toml` basename is read as native TOML; any other suffix is silently empty. Options typed as strings stay strings. |
| coverage.py                                                                         | `.config/checks/coverage/coverage.toml`                                            | `--rcfile`. `[run]` tables are accepted in an explicit TOML file.                                                                                                  |
| Ruff, ty, taplo, Lychee, Gitleaks, OSV-Scanner, typos, golangci-lint, import-linter | `.config/checks/<tool>/<tool>.toml`                                                | Each takes an explicit flag that replaces discovery.                                                                                                               |
| Prettier                                                                            | `.config/checks/prettier/prettier.toml`, `prettierignore`                          | `--config` and `--ignore-path`. `overrides[].files` resolve relative to the configuration directory.                                                               |
| markdownlint-cli2, knip                                                             | `.config/checks/<tool>/<tool>.toml`                                                | An explicit TOML path. A discovered file still merges, so none may remain.                                                                                         |
| Vale, yamllint, ShellCheck, pre-commit, ESLint, actionlint, Syft, GoReleaser, c8    | `.config/checks/<tool>/` or `.config/release/<tool>/`, in the tool's native format | These tools do not read TOML.                                                                                                                                      |
| codespell                                                                           | `.config/checks/codespell/codespell.toml`                                          | `--toml`, which reads only a `[tool.codespell]` table.                                                                                                             |
| deptry                                                                              | `.config/checks/deptry/policy.toml`                                                | Its explicit configuration is also read as the dependency manifest, so the runner passes the repository parameters as options.                                     |
| npm                                                                                 | `.config/npm/npmrc`                                                                | Bound by the toolchain owner through `NPM_CONFIG_USERCONFIG`, with the global layer cleared.                                                                       |
| mise                                                                                | `.config/mise/config.toml`, `.config/mise/mise.lock`, `.config/miserc.toml`        | Native discovery.                                                                                                                                                  |
| hatchling, mutmut                                                                   | `pyproject.toml` tables                                                            | Neither accepts an explicit configuration path.                                                                                                                    |
| Nox                                                                                 | root `noxfile.py`                                                                  | Nox changes into the file's directory, so the runner entry stays at the root.                                                                                      |

### 4. A closed root catalog and explicit binding

The root admits these classes:

- entry documents (`AGENTS.md`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE`, `NOTICE`, `VERSION`);
- Git and editor protocol files (`.gitignore`, `.gitattributes`, `.editorconfig`);
- Forge entries (`.github/`, `.gitlab/`, `.gitlab-ci.yml`);
- the ETHOS, OpenSpec and agent roots (`.ethos/`, `openspec/`, `.agents/`);
- each applied module's manifests, locks and runner entry, for example `pyproject.toml`, `uv.lock` and `noxfile.py`, or `package.json` and `package-lock.json`, or `go.mod` and `go.sum`.

Non-dot directories are product-owned. Every invocation the repository owns passes configuration explicitly. Root pointer files such as an extending `ruff.toml`, and tool policy embedded in manifests, are not admitted.

The cost: a bare `ruff` or `pytest` in the root no longer applies project policy. The `fix` and `check` verbs and documented editor settings replace that discovery. One explicit path for every consumer is preferred over a second entry for the same policy.

### 5. The binding file set and gate storage

`.ethos/` holds only the four files the runtime defines schemas for: `profile.toml`, `workspace.toml`, `release.toml` and `rules.toml`. `assistants.toml`, `project.toml` and tracked `state/` belong to superseded binding schemas.

Gates are declared inline in the profile, or the profile selects the packaged ETHOS gate registry. ETHOS proves itself with its own product gates. Repository-local registry files (`.ethos/gates.toml`, `system/gates.toml` in adopters) move inline.

### 6. Commit, branch and release conventions

- **Commit types:** the grammar admits the ten types that every declared policy shares. `spec` and `style` exist in only some policies, and their commits map to `docs` and `refactor`.
- **Commit scopes:** a scope is optional because four of six policies make it optional. A repository may declare a closed scope list that admission enforces.
- **Signing:** SSH signing is required.
- **Branch roles:** they take the majority names. Work Lane worktrees use the workstation layout `<repository>-worktrees/<yyyymmdd>-<slug>/`, which becomes the ETHOS default instead of an opt-in.
- **Releases:**
  - Released products keep `VERSION` as the only version source. It is the majority encoding and it is language-neutral.
  - Tags are `v` followed by a SemVer version.
  - The changelog is Keep a Changelog 1.1.0 with bracketed headings.

### 7. Documentation keeps DR-0011

DR-0011 decided that the portable documentation contract is the profile docs root plus `subject`, `role`, `state` and `relations` metadata. This Change fixes only two encodings:

- Metadata is YAML front matter, the form ETHOS and its registry use.
- Decision records, where a repository keeps any, are named `dr-NNNN-<topic>.md`.

Subject layout stays repository-owned, and no repository needs a decisions directory.

### 8. Formatting and text normalization

The workstation rule names the common formatters:

- Prettier formats Markdown and YAML, with preserved prose wrapping and width 100.
- taplo formats TOML.

Both are bound through `fix` and `check`. ETHOS adopts Prettier for its own Markdown in this Change; today it only lints it. `.editorconfig` and `.gitattributes` declare UTF-8, LF and a final newline in every repository, because every repository holds text that agents and editors write.

### 9. Toolchain owner and verbs

One locked owner selects tools:

- `.config/mise/`, with locked resolution and an early-init `miserc.toml` that ignores parent and global configuration, when tools beyond the package manager are needed;
- otherwise the package manager and its lockfile.

`bootstrap`, `fix` and `check` are tasks of that owner. A uv-only repository uses mise for its tasks, because uv has no task runner.

### 10. CI for several Forges is one model

The repositories that publish to two Forges and generate both files from `.config/ci/pipeline.cue` show the practice works. The others hand-write two files that already drift. The model and its drift check become an obligation only when more than one Forge is targeted.

### 11. Names

Repository-authored names use lowercase kebab-case. Exemptions follow the tool catalog and ecosystem modules: Python modules and test files, Go packages and test files, entry documents, and basenames a tool requires.

## Risks / Trade-offs

- **Churn across every adopter.** Mitigation: each repository migrates in one Change that lands together with its runtime switch. The audit names the canonical repair for every gap.
- **Concurrent Work Lanes in ETHOS and aigw-cli.** Mitigation: migrations start only after the current lane holders land or agree. Landing re-reads live references.
- **Secret scanning continuity during migration.** Pre-commit admission reads canonical paths only after the runtime switch. Mitigation: move the configuration and switch runtime in the same batch, with no commit in between.
- **Bare tool invocation loses project policy.** Accepted. The verbs and editor settings carry the explicit paths.
- **Strict TOML loaders.** Pytest treats an explicit TOML file as native configuration only under the basename `pytest.toml`, and its string-typed options must stay strings. Mitigation: the tool catalog records the basename, and migration checks prove the strict options take effect.
- **The deferred families diverge for longer.** Accepted under the workstation rule. Their later Changes consume the same contract.

## Migration Plan

1. ETHOS:
   - land the contract, the evaluation points and the amended governance documents;
   - conform ETHOS itself: configuration groups, root pointers, the Prettier binding, names and front matter;
   - release a runtime that carries the paradigm.
2. Each adopter, through its own Change, in one batch:
   - move carriers to the canonical paths;
   - adapt the consumers that pass those paths;
   - land;
   - switch the repository's runtime.

   Order: the proxy, aigw-cli, data-department-work-guidelines, architecture-publisher (which also gains `AGENTS.md`), web-ingestion-benchmark, the two films, then architecture-publications. A repository with foreign Work Lanes migrates after its holders land or agree.

3. The alphasim and di-effect families follow in their own later migrations.

Rollback: before an adopter switches runtime, its migration reverts by an ordinary revert. After the switch, the previous runtime stays selectable through `ethos hook install --runtime`.

## Open Questions

- Root ignore files that only agent indexers read, such as `.cbmignore`: admit them to the root catalog, or move the indexers to explicit configuration. Decide when the first adopter migration meets one.
