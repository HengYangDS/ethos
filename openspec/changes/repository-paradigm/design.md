## Context

A read-only inventory on 2026-10-14 covered the thirteen Git repositories that track an ETHOS binding: ETHOS, the OpenAI Responses Proxy, aigw-cli, architecture-publisher, architecture-publications, data-department-work-guidelines, two introduction films, web-ingestion-benchmark, two alphasim clones and two di-effect clones. One di-effect clone tracks no binding, and one alphasim repository is a clone of the other.

Shared by every repository where the concern applies:

- `README.md` and `openspec/config.yaml`;
- `.ethos/profile.toml`;
- `build/` ignored as the generated root;
- Python 3.12 as the compatibility floor;
- a formatter width of 100;
- SSH-signed Conventional Commits;
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
- hand-maintained CI files for two Forges in three repositories;
- orchestration as native owner tasks, or as shell scripts that run only where a POSIX shell exists.

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
- **Path level:** prewrite evaluates each path it would create with the report's own path obligations, so a non-conforming path is refused before it is written.
- **Staged:** pre-commit admission reads Gitleaks and Ruff configuration from their canonical paths.

Alternatives rejected:

- A per-repository paradigm file: it recreates per-repository improvisation.
- A new gate or command: the audit already owns profile-independent governance.
- A documented convention without enforcement: the inventory shows conventions drift without an owner.
- Restating the path obligations as CEL topology rules: the same obligations would have a second owner that can disagree with the report.

### 3. Configuration groups by consuming tool, not by concern

`.config/checks/<owner>/` and `.config/release/<owner>/` are named by the consuming tool, or by a repository check when only repository-owned parameters exist. The Config Boundary Model already separates how a tool runs (its configuration) from why it runs (the profile and gate catalog), and directory names follow the first.

A shared concern vocabulary did emerge (`secrets`, `prose`, `markdown`, `toml` and `links` appear in several repositories), but it fails mechanically:

- Ruff serves lint and format.
- Prettier formats several file types.
- `dependencies` mixes deptry and OSV-Scanner.

A repository check that has only repository-owned parameters names its directory after the check and keeps them in `policy.toml`. A tool-native file name found in another owner directory is reported with the tool's canonical carrier.

A concern vocabulary would need an ETHOS-owned assignment of every tool to a concern, which is an opinion table. A tool catalog maps canonical basenames to tool identifiers, which are facts from each tool's documentation. Concern grouping stays in the profile or a repository responsibility catalog.

The packaged contract holds the complete tool catalog as executable data. The rows below were verified against the locked versions in the fleet and fix the encodings that a migration must get right.

| Tool                                                                                | Canonical carrier                                                                  | Binding and constraint                                                                                                                                                                    |
| ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| pytest                                                                              | `.config/checks/pytest/pytest.toml`                                                | `-c` together with `--rootdir`. Only the `pytest.toml` basename is read as native TOML; any other suffix is silently empty. Options typed as strings stay strings.                        |
| coverage.py                                                                         | `.config/checks/coverage/coverage.toml`                                            | `--rcfile`. `[run]` tables are accepted in an explicit TOML file.                                                                                                                         |
| Ruff, ty, taplo, Lychee, Gitleaks, OSV-Scanner, typos, golangci-lint, import-linter | `.config/checks/<tool>/<tool>.toml`                                                | Each takes an explicit flag that replaces discovery.                                                                                                                                      |
| Prettier                                                                            | `.config/checks/prettier/prettier.toml`, `prettierignore`                          | `--config` and `--ignore-path`. `overrides[].files` resolve relative to the configuration directory.                                                                                      |
| knip                                                                                | `.config/checks/knip/knip.toml`                                                    | An explicit TOML path. A discovered file still merges, so none may remain.                                                                                                                |
| TypeScript                                                                          | `.config/checks/typescript/tsconfig.json`                                          | `tsc --project` and Knip's `typescript.config`. Paths in the project resolve relative to its own directory.                                                                               |
| markdownlint-cli2                                                                   | `.config/checks/markdownlint-cli2/.markdownlint-cli2.yaml`                         | `--config`. It parses TOML, but markdownlint 0.41.1 drops rule options from TOML tables (it tests `instanceof Object`, and smol-toml tables have no prototype), so the native YAML stays. |
| Vale, yamllint, ShellCheck, pre-commit, ESLint, actionlint, Syft, GoReleaser, c8    | `.config/checks/<tool>/` or `.config/release/<tool>/`, in the tool's native format | These tools do not read TOML.                                                                                                                                                             |
| codespell                                                                           | `.config/checks/codespell/codespell.toml`                                          | `--toml`, which reads only a `[tool.codespell]` table.                                                                                                                                    |
| deptry                                                                              | `.config/checks/deptry/policy.toml`                                                | Its explicit configuration is also read as the dependency manifest, so the runner passes the repository parameters as options.                                                            |
| npm                                                                                 | `.config/npm/npmrc`                                                                | Bound by the toolchain owner through `NPM_CONFIG_USERCONFIG`, with the global layer cleared.                                                                                              |
| mise                                                                                | `.config/mise/config.toml`, `.config/mise/mise.lock`, `.config/miserc.toml`        | Native discovery.                                                                                                                                                                         |
| hatchling, mutmut                                                                   | `pyproject.toml` tables                                                            | Neither accepts an explicit configuration path.                                                                                                                                           |
| Nox                                                                                 | root `noxfile.py`                                                                  | Nox changes into the file's directory, so the runner entry stays at the root.                                                                                                             |

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
- **Signing:** every commit carries an SSH signature. The paradigm fixes the signature, so `[commit_policy]` only restricts scopes and constrains identities, and a repository without one gets the paradigm's commit policy. The repair deletes a restated `signing_required` or `signing_format`. ETHOS runs Git without global configuration, so each repository keeps its lifecycle signer and trust anchor in local configuration. Commit creation owns the signer check. Status reports it and blocks only in the roles that create lifecycle commits, so a CI clone that only verifies is not blocked. Formation takes the creator's signer and trust anchor as reviewed plan inputs and writes them into the new repository before it signs the initial commit.
- **Branch roles:** they take the majority names. Work Lane worktrees use the workstation layout `<repository>-worktrees/<yyyymmdd>-<slug>/`, which becomes the ETHOS default instead of an opt-in.
- **Release mirror:** whether the release branch follows the accepted branch is a release fact, so `.ethos/release.toml` declares it as `[release] mirror = "accepted_ff"`; it is independent otherwise. `.ethos/workspace.toml` keeps only `[commit_policy]`, and a repository without one tracks no workspace binding. The repair moves an `accepted_ff` mirror and deletes `[branch_roles]` and tables no reader consults, such as `[[package]]`.
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

The workstation blank-line rule applies to every repository, so blank lines are what the formatters write for the parsed structure. Ruff formats Python wherever Python is tracked, because it is the only Python formatter in the fleet and the rule has no other enforcer.

The contract holds each formatter's common settings, so a repository cannot keep its own width or wrapping. Current authored OpenSpec Markdown and YAML use the same Prettier fix/check owner as other authored carriers. Official OpenSpec still owns artifact structure, task and requirement meaning, validation and archive; formatting grants none of those lifecycle effects. Preserved prose wrapping and native code spans retain literal names such as `operation-intent-*`. Archived records and captured upstream sources keep their immutable owner and are excluded from writes.

The official CLI copies delta blocks verbatim into main specs and creates a new spec's `## Purpose` without a blank line. Prettier can also change emphasis spelling inside requirement names, whose exact text participates in archive matching. These observations remain acceptance inputs: task 3.7 must exercise real archive projection and preserve requirement identity through the native formatter boundary, rather than exempt all current OpenSpec source or modify official tool source. Semantic lint accepts the formatter's own output without an emphasis-style rule; Prettier writes underscores around words but asterisks inside a word.

The size ceilings are shared too: 512 effective lines for each Python file and 512 nonblank lines for each current authored Markdown document. The Python ceiling was a value in ETHOS's own `.ethos/rules.toml` that no adopter declared, so adopters had none. The Markdown ceiling was a product constant of 500, while task 12.4 of the proof-throughput Change records 512. The contract now holds both values. The paradigm report measures Python files, and docs health reads the Markdown value from the contract. The Markdown requirement itself stays in the proof-throughput quality specification. The paradigm report is the only Python size check: ETHOS removed its `python-size` gate once its gate registry could change through ordinary landing (decision 15).

### 9. Toolchain owner and verbs

One locked owner selects tools:

- `.config/mise/`, with locked resolution and an early-init `miserc.toml` that ignores parent and global configuration, when tools beyond the package manager are needed;
- otherwise the package manager and its lockfile.

`bootstrap`, `fix` and `check` are tasks of that owner. A uv-only repository uses mise for its tasks, because uv has no task runner.

### 10. Orchestration is native

Every repository orchestrates its verbs, gates and CI. Of the nine repositories outside the deferred families, only architecture-publications and the two introduction films do this through native commands and owner tasks alone. ETHOS and architecture-publisher also track shell scripts, as both deferred families do, and five repositories embed shell programs in CI steps. A script runs only where its interpreter exists, so it fails the Windows hosts that the verbs serve. The workstation rule already requires native execution, so the paradigm picks the native encoding:

- Verbs, gates, CI steps and release steps call native tool commands or toolchain-owner tasks. A CI step calls one command; wiring a single native command into CI is not orchestration.
- A tracked file with a shell or PowerShell suffix or shebang conforms only as the output of an official generator that the packaged tool catalog names, such as `mise generate bootstrap`. Its generator version and output digest are recorded for `check` to verify.
- No other script class is admitted today. A repository that demonstrates necessary operating-system glue brings an ETHOS Change that adds the class with its owner, necessity, scope and target-platform evidence. There is no repository-local exception list.

Rewriting the same controller in another language does not satisfy this decision. The repair moves the behaviour into the owning product's native command or an owner task.

### 11. CI for several Forges is one model

The repositories that publish to two Forges and generate both files from `.config/ci/pipeline.cue` show the practice works. The others hand-write two files that already drift. The model and its drift check become an obligation only when more than one Forge is targeted. The model is CUE, as in all three repositories that publish to two Forges; a tracked `.gitlab-ci.yml` and workflow files directly under `.github/workflows/` mark the two Forges.

### 12. Names

Repository-authored names use lowercase kebab-case. Exemptions follow the tool catalog and ecosystem modules: Python modules and test files, Go packages and test files, entry documents, and basenames a tool requires. A leading `.` or `_` marker, as in the `docs/_meta` that the docs registry reads, and dot-separated suffixes are not word separators.

A name that another obligation judges keeps that obligation's single gap: root entries, binding files, configuration owners and decision records. Prewrite judges a new file's own name; the report judges directories, because only the whole tree shows whether a directory holds Python or Go modules. A rename must update its references, so the repair stays report-only.

### 13. Ecosystem modules stay thin

Each module holds only what every repository of that ecosystem shares:

- **Python:** `pyproject.toml` locked by `uv.lock`, and a 3.12 lower bound.
- **Node:** `package-lock.json` whenever npm dependencies are declared.
- **Go:** `go.mod` with `go.sum` whenever it requires modules.

The two films use uv without any linter or formatter. A required Ruff linter or pytest would therefore impose a tool rather than extract a shared practice. Ruff's formatter is the exception, because the shared blank-line rule needs it (decision 8). Where a tool is configured, the core rules place it and the tool catalog names its file.

Every explicit formatter width in the fleet is already 100, so a configured formatter keeps 100, and Ruff targets the shared 3.12 floor. Runtime and tool versions stay repository values under the workstation version policy, so a version bump never needs an ETHOS Change.

### 14. Common OpenSpec rules

A repository that tracks OpenSpec artifacts selects `spec-driven`, and each artifact's rules begin with the contract's common rules. They come from the workstation's OpenSpec task rule, the official templates and delta semantics and ETHOS's lifecycle order, and they keep what recurs across the adopters' own rules:

- the official templates and native delta operations;
- falsifiable requirements;
- one semantic owner per behavior;
- truthful, dependency-ordered tasks;
- execution history kept with its native evidence owners.

Not every adopter states these rules today. The films and architecture-publications declare no rules, and two adopters keep rules that contradict them: aigw-cli keeps execution results in design.md, and web-ingestion-benchmark tracks closeout as checkable tasks. Their migration Changes remove or rewrite those rules, because the workstation rule forbids both.

A repository's own rules follow the common ones. The repair keeps those rules, their lines and their comments, and drops only exact copies of a common rule. Whether an own rule restates or contradicts a common one is a judgment for the repository's migration Change.

A repository that selects another schema keeps that gap report-only, because its Changes are written against that schema's artifacts.

### 15. The product registry is recognized by history

ETHOS's own `system/gates.toml` keeps the plain registry owner because the evaluated commit shares Git history with the commit the running build came from. Until now the test was byte equality with the running build's packaged registry, so every edit of ETHOS's registry looked like an adopter registry. The installed runtime then applied the adopter quality floor, which ETHOS's registry cannot satisfy, and registry edits reached dev only through break-glass ref updates.

Shared history gives the same answer in every runtime that judges ETHOS: the lane source, the installed hook runtime and a release wheel. A repository without that history keeps the adopter floor, even for a verbatim copy of the product registry. Deciding by gate profiles or `profile_id` was rejected, because an adopter could omit `profile` or name itself `ethos` to escape the floor. Giving ETHOS's registry verifiers that satisfy the floor remains the long-term alternative; it is a much larger change.

The classification is not part of the policy projection. The incumbent runtime therefore admits the classification change while the registry is unchanged, and the `python-size` removal follows as an ordinary registry edit judged by the new runtime.

## Risks / Trade-offs

- **Churn across every adopter.** Mitigation: each repository migrates in one Change that lands together with its runtime switch. The audit names the canonical repair for every gap.
- **Concurrent Work Lanes in ETHOS and aigw-cli.** Mitigation: migrations start only after the current lane holders land or agree. Landing re-reads live references.
- **Secret scanning continuity during migration.** Pre-commit admission reads canonical paths only after the runtime switch. Mitigation: move the configuration and switch runtime in the same batch, with no commit in between.
- **Bare tool invocation loses project policy.** Accepted. The verbs and editor settings carry the explicit paths.
- **Owners the incumbent runtime reads by path.** Pre-commit admission runs the selected runtime, which finds projection declarations only at the paths it knows. Mitigation: a runtime first registers both the incumbent and the canonical path, and the declarations move in a later batch under that runtime.
- **Strict TOML loaders.** Pytest treats an explicit TOML file as native configuration only under the basename `pytest.toml`, and its string-typed options must stay strings. Mitigation: the tool catalog records the basename, and migration checks prove the strict options take effect.
- **The deferred families diverge for longer.** Accepted under the workstation rule. Their later Changes consume the same contract.
- **A product registry edit no longer meets an accidental veto.** Accepted. Closeout's control replacement records a removed or weakened required gate; enforcing an independent review of that record needs a declared independent verification, which ETHOS does not declare today. A fork that carries ETHOS's history counts as the product.

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

   Order: a repository without foreign Work Lanes or other blockers migrates first; otherwise the order follows dependencies and current lane state, and a repository with foreign Work Lanes migrates after its holders land or agree. The adopters are the proxy, aigw-cli, data-department-work-guidelines, architecture-publisher (which also gains `AGENTS.md`), web-ingestion-benchmark, the two films and architecture-publications.

3. The alphasim and di-effect families follow in their own later migrations.

Rollback: before an adopter switches runtime, its migration reverts by an ordinary revert. After the switch, the previous runtime stays selectable through `ethos hook install --runtime`.
