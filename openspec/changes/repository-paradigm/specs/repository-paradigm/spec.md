## Purpose

Defines the common repository contract that every ETHOS-governed repository, ETHOS included, satisfies, and the uniform conformance verdict that ETHOS derives from it.

## ADDED Requirements

### Requirement: One paradigm governs every repository

ETHOS SHALL evaluate every governed repository, ETHOS included, against one repository paradigm that ETHOS owns. The paradigm SHALL contain only obligations shared by every governed repository, plus ecosystem modules that apply exactly when a repository uses that ecosystem. A repository SHALL NOT declare paradigm exceptions; changing an obligation SHALL require an ETHOS Change.

#### Scenario: A repository declares an exception

- **WHEN** a repository binding names a paradigm exception or an unknown paradigm option
- **THEN** strict binding validation fails closed
- **AND** the obligation is still evaluated.

#### Scenario: An ecosystem module is not used

- **WHEN** a repository tracks no `package.json`
- **THEN** no Node module obligation is evaluated for it.

### Requirement: Product layout remains repository-owned

The paradigm SHALL NOT prescribe product or domain structure. Source trees, content, media, test organization, documentation subject layout and provider shape SHALL remain the repository's choice, provided they do not occupy a carrier that the paradigm owns.

#### Scenario: Different product shapes conform

- **WHEN** one repository keeps `cmd/` and `internal/` and another keeps `content/` and `media/`
- **THEN** neither receives a paradigm gap for those trees.

### Requirement: The root carries only protocol entries

Every tracked root file and dot-directory SHALL belong to the paradigm root catalog: entry documents, Git and editor protocol files, Forge entries, the ETHOS, OpenSpec and agent roots, and the manifests, locks and runner entry of an applied ecosystem module. Non-dot root directories SHALL remain product-owned.

#### Scenario: Tool configuration sits at the root

- **WHEN** the root tracks `pytest.ini` or `.prettierrc.json`
- **THEN** the paradigm reports a misplaced configuration with its canonical `.config/` path.

#### Scenario: An agent-specific entry is tracked

- **WHEN** the root tracks `CLAUDE.md` or a host projection root such as `.claude/`
- **THEN** the paradigm reports an unadmitted root entry.

### Requirement: Agent and reader entry is singular

Every governed repository SHALL keep `AGENTS.md` and `README.md` at its root. `AGENTS.md` SHALL be the only agent entry; repository-local Skills SHALL live under `.agents/skills/`.

#### Scenario: A repository lacks the agent entry

- **WHEN** a governed repository has no root `AGENTS.md`
- **THEN** the paradigm reports a missing entry document.

### Requirement: Tool configuration lives in the configuration plane

Tool configuration SHALL live under `.config/checks/<owner>/`, `.config/release/<owner>/`, `.config/ci/`, or a toolchain root: `.config/mise/` and the package-manager roots it binds. `<owner>` SHALL name the consuming tool, or the repository check when only repository-owned parameters exist. Native files SHALL keep the tool's canonical basename and repository-owned parameters SHALL be `policy.toml`.

#### Scenario: Configuration is grouped by concern

- **WHEN** Gitleaks configuration is tracked as `.config/checks/secrets/policy.toml`
- **THEN** the paradigm reports its canonical path `.config/checks/gitleaks/gitleaks.toml`.

#### Scenario: Native and repository parameters share an owner

- **WHEN** `.config/checks/coverage/` holds `coverage.toml` and a repository-owned floor in `policy.toml`
- **THEN** both files conform.

### Requirement: Configuration uses TOML where the tool reads TOML

When the consuming tool reads TOML configuration, its tracked configuration SHALL be TOML. Another format SHALL be used only for a tool that cannot read TOML, and then in that tool's native format.

#### Scenario: A TOML-capable tool uses JSON

- **WHEN** Prettier configuration is tracked as JSON
- **THEN** the paradigm reports that the configuration must be TOML.

#### Scenario: A tool without TOML support

- **WHEN** Vale configuration is tracked as `vale.ini`
- **THEN** it conforms.

### Requirement: The configuration plane holds only consumed configuration

Every tracked file under `.config/` SHALL be consumed by a tool or a repository check. Documentation, scripts, plans, inventories, evidence and generated output SHALL NOT live under `.config/`.

#### Scenario: Explanation is placed in the configuration plane

- **WHEN** `.config/README.md` or `.config/checks/secrets/README.md` is tracked
- **THEN** the paradigm reports a non-configuration carrier.

### Requirement: Configuration is bound explicitly

Repository-owned invocations SHALL pass tool configuration paths explicitly. The paradigm SHALL NOT admit a root file whose purpose is to point a tool at `.config/`. Package manifests SHALL carry packaging, dependency and workspace metadata, not the policy of a tool that accepts an explicit configuration file.

#### Scenario: A root pointer remains

- **WHEN** a root `ruff.toml` only extends `.config/checks/ruff/ruff.toml`
- **THEN** the paradigm reports an unadmitted root pointer.

#### Scenario: Tool policy is embedded in a manifest

- **WHEN** `pyproject.toml` declares `[tool.pytest.ini_options]`
- **THEN** the paradigm reports embedded tool policy with its canonical path.

### Requirement: Staged admission reads canonical configuration

When a repository configures secret scanning or the staged Python format check, native pre-commit admission SHALL use the configuration at its canonical `.config/` path. Configuration found anywhere else SHALL be reported as a gap and SHALL NOT silently disable the check.

#### Scenario: Secret scanning configuration moves

- **WHEN** Gitleaks configuration exists only at `.config/checks/gitleaks/gitleaks.toml`
- **THEN** pre-commit admission scans the staged content with that configuration.

### Requirement: The binding uses only ETHOS-defined files

The tracked `.ethos/` binding SHALL contain only `profile.toml`, `workspace.toml`, `release.toml` and `rules.toml`. A repository SHALL declare its proof gates in `profile.toml` or select the packaged ETHOS gate registry; repository-local registry files SHALL NOT exist.

#### Scenario: A legacy binding file is tracked

- **WHEN** `.ethos/assistants.toml`, `.ethos/project.toml` or `.ethos/gates.toml` is tracked
- **THEN** the paradigm reports a binding file outside the ETHOS schema set.

### Requirement: OpenSpec carries the common rules

Every governed repository SHALL use the `spec-driven` schema and include the ETHOS common artifact rules in `openspec/config.yaml`. Repository-specific rules SHALL only be appended to those common rules.

#### Scenario: The common task rule is missing

- **WHEN** a repository configuration omits the common tasks rule
- **THEN** the paradigm reports the missing common rule.

### Requirement: Commits follow one grammar

Every governed repository SHALL declare the common commit policy: the Conventional Commit types build, chore, ci, docs, feat, fix, perf, refactor, revert and test, an optional lowercase kebab-case scope, an optional breaking marker, and required SSH signing. A declared scope list SHALL restrict scopes; the type set SHALL NOT vary.

#### Scenario: A repository adds a type

- **WHEN** a repository commit policy admits a `spec` or `style` type
- **THEN** the paradigm reports a non-common commit grammar.

#### Scenario: A scope list is declared

- **WHEN** a repository declares the scopes `cli` and `relay`
- **THEN** commit admission rejects `fix(other): repair`.

### Requirement: Branch roles and Work Lanes use the standard names

Every governed repository SHALL use the release branch `main`, the accepted branch `dev`, the candidate branch `candidate/dev`, the Work Lane prefix `work/` and the proposal prefix `proposal/`. Work Lane worktrees SHALL be siblings at `<repository>-worktrees/<yyyymmdd>-<slug>/`.

#### Scenario: A review prefix differs

- **WHEN** a workspace declares `submit/` as its proposal prefix
- **THEN** the paradigm reports a non-standard branch role.

### Requirement: Released products keep one version source

A repository that publishes releases SHALL keep `VERSION` as its only version source and SHALL tag releases as `v` followed by a Semantic Versioning version. `CHANGELOG.md` SHALL follow Keep a Changelog 1.1.0 with an `[Unreleased]` section and bracketed version headings.

#### Scenario: A second version source exists

- **WHEN** a released repository keeps a literal version in `package.json` and in `VERSION`
- **THEN** the paradigm reports two version sources.

#### Scenario: A version heading is unbracketed

- **WHEN** `CHANGELOG.md` contains `## 1.2.0 - 2026-10-14`
- **THEN** the paradigm reports a non-standard version heading.

### Requirement: Documents carry YAML front matter

Documentation under the profile docs root SHALL begin with YAML front matter that carries `subject`, `role`, `state` and `relations`. Metadata SHALL NOT be wrapped in comments or another syntax.

#### Scenario: Metadata is wrapped in a comment

- **WHEN** a document carries its metadata inside an HTML comment
- **THEN** the paradigm reports non-standard front matter.

### Requirement: Decision records use one name grammar

A repository that keeps decision records SHALL name each `dr-NNNN-<topic>.md`, with a four-digit number and a lowercase kebab-case topic. A repository without decision records SHALL NOT need a decisions directory.

#### Scenario: A decision record uses another prefix

- **WHEN** a decision record is named `adr-0004-storage.md` or `DR-0004-storage.md`
- **THEN** the paradigm reports a non-standard decision record name.

### Requirement: Text formatting uses the common formatters

Markdown and YAML SHALL be formatted by Prettier with preserved prose wrapping and a print width of 100, and TOML by taplo. Both SHALL be bound through the repository's `fix` and `check` verbs with configuration under `.config/checks/`.

#### Scenario: Markdown is only linted

- **WHEN** a repository tracks Markdown and has no Prettier configuration in the configuration plane
- **THEN** the paradigm reports a missing Markdown formatter binding.

### Requirement: Text normalization is declared

Every governed repository SHALL keep `.editorconfig` and `.gitattributes` that select UTF-8, LF line endings and a final newline for tracked text.

#### Scenario: Line endings are undeclared

- **WHEN** a governed repository has no `.gitattributes`
- **THEN** the paradigm reports missing text normalization.

### Requirement: Configured formatters share one width

Every configured formatter SHALL use a line width of 100, including Prettier, taplo and Ruff. A repository that configures Ruff SHALL also target Python 3.12.

#### Scenario: A formatter keeps its default width

- **WHEN** a repository's Ruff configuration sets or defaults to a line length of 88
- **THEN** the paradigm reports a non-common formatter width.

### Requirement: Ecosystem modules lock their manifests

A repository that tracks `pyproject.toml` SHALL lock it with `uv.lock` and SHALL declare a Python lower bound of 3.12. A repository that declares npm dependencies SHALL lock them with `package-lock.json`, and a repository that tracks `go.mod` SHALL track `go.sum`. Tool and runtime versions remain repository-owned under the version policy.

#### Scenario: A Python manifest is unlocked

- **WHEN** a repository tracks `pyproject.toml` without `uv.lock`
- **THEN** the paradigm reports an unlocked Python module.

#### Scenario: A manifest without dependencies

- **WHEN** a repository's `package.json` declares only scripts
- **THEN** no npm lock is required.

### Requirement: One locked toolchain owner exposes the common verbs

A repository SHALL select its toolchain through one locked owner: `.config/mise/` with locked resolution when it needs tools beyond its package manager, otherwise its package manager and lockfile. That owner SHALL expose `bootstrap`, `fix` and `check` as tasks.

#### Scenario: Toolchain configuration sits at the root

- **WHEN** a repository tracks a root `mise.toml`
- **THEN** the paradigm reports its canonical path `.config/mise/config.toml`.

#### Scenario: A verb is missing

- **WHEN** the toolchain owner exposes no `fix` task
- **THEN** the paradigm reports a missing common verb.

### Requirement: CI for several Forges is one model

A repository that runs CI on more than one Forge SHALL define its pipelines once under `.config/ci/` and generate each Forge file from that model. `check` SHALL fail when a generated Forge file differs from the model.

#### Scenario: Two Forge files are maintained by hand

- **WHEN** a repository tracks `.gitlab-ci.yml` and `.github/workflows/` without a model under `.config/ci/`
- **THEN** the paradigm reports an unmodeled multi-Forge pipeline.

### Requirement: Repository-authored names use lowercase kebab-case

Repository-authored file and directory names SHALL use lowercase kebab-case, except where an ecosystem or tool fixes the name, such as Python modules, Go packages, entry documents and tool-required basenames.

#### Scenario: A rule file uses snake_case

- **WHEN** a repository tracks `rules/module_layout.md`
- **THEN** the paradigm reports a non-standard name with its kebab-case form.

### Requirement: Paradigm conformance is a blocking verdict

The repository audit SHALL report every paradigm gap with its carrier, the violated obligation and the canonical repair. While any gap remains, prove, land and publish SHALL be blocked. Prewrite admission SHALL refuse a write that would create a path the paradigm rejects.

#### Scenario: A repository conforms

- **WHEN** a governed repository has no paradigm gap
- **THEN** the audit reports a passing paradigm report and does not block.

#### Scenario: A non-conforming path is requested

- **WHEN** a Work Lane requests prewrite admission for a new root `pytest.ini`
- **THEN** admission refuses the path and names `.config/checks/pytest/pytest.toml`.
