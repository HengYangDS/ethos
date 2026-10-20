# repository-paradigm Specification

## Purpose

Defines the common repository contract that every ETHOS-governed repository, ETHOS included, satisfies, and the uniform conformance verdict that ETHOS derives from it.

## Requirements

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

- **WHEN** Gitleaks configuration is tracked as `.config/checks/secrets/gitleaks.toml`
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

#### Scenario: A TypeScript project is passed explicitly

- **WHEN** a repository keeps its TypeScript project at `.config/checks/typescript/tsconfig.json` and passes it to `tsc --project` and to Knip's `typescript.config`
- **THEN** the carrier conforms in Python, Node and Go repositories
- **AND** a root `tsconfig.json` or `jsconfig.json` is reported with that canonical path.

### Requirement: Staged admission reads canonical configuration

When a repository configures secret scanning or the staged Python format check, native pre-commit admission SHALL use the configuration at its canonical `.config/` path. Configuration found anywhere else SHALL be reported as a gap and SHALL NOT silently disable the check.

#### Scenario: Secret scanning configuration moves

- **WHEN** Gitleaks configuration exists only at `.config/checks/gitleaks/gitleaks.toml`
- **THEN** pre-commit admission scans the staged content with that configuration.

### Requirement: The binding uses only ETHOS-defined files

The tracked `.ethos/` binding SHALL contain only `profile.toml`, `workspace.toml`, `release.toml` and `rules.toml`. A repository SHALL declare its proof gates in `profile.toml` or select the packaged ETHOS gate registry; repository-local registry files SHALL NOT exist. `workspace.toml` SHALL declare only `[commit_policy]`, and a repository that declares none SHALL NOT track it.

#### Scenario: A legacy binding file is tracked

- **WHEN** `.ethos/assistants.toml`, `.ethos/project.toml` or `.ethos/gates.toml` is tracked
- **THEN** the paradigm reports a binding file outside the ETHOS schema set.

#### Scenario: A workspace declares a table no reader consults

- **WHEN** `.ethos/workspace.toml` declares `[[package]]`
- **THEN** the paradigm reports the table and the repair deletes it.

#### Scenario: A workspace binding declares nothing else

- **WHEN** `.ethos/workspace.toml` declares only `[branch_roles]` with `release_mirror = "independent"`
- **THEN** the repair deletes `.ethos/workspace.toml`.

### Requirement: OpenSpec carries the common rules

Every governed repository that tracks OpenSpec artifacts SHALL select the `spec-driven` schema in `openspec/config.yaml`, and each artifact's rules SHALL begin with the common rules that the paradigm contract holds. Repository-specific rules SHALL only follow those common rules.

#### Scenario: The common task rule is missing

- **WHEN** a repository configuration omits the common tasks rule
- **THEN** the paradigm reports the missing common rule.

#### Scenario: Repository rules come before the common rules

- **WHEN** a configuration lists only its own proposal rule, in a flow sequence
- **THEN** the repair rewrites the proposal rules as a block sequence that begins with the common rules and keeps the repository's rule after them, leaving every other key and comment unchanged.

#### Scenario: A repository selects its own schema

- **WHEN** a configuration selects a schema other than `spec-driven`
- **THEN** the paradigm reports the schema, and the repair leaves that gap report-only.

#### Scenario: A repository tracks no OpenSpec artifact

- **WHEN** a repository tracks no path under `openspec/`
- **THEN** the paradigm reports no OpenSpec gap.

### Requirement: Commits follow one grammar and carry an SSH signature

Every governed repository SHALL use the commit subject grammar that the paradigm contract holds: the Conventional Commit types build, chore, ci, docs, feat, fix, perf, refactor, revert and test, an optional lowercase kebab-case scope and an optional breaking marker `!`. Every commit SHALL carry an SSH signature. `[commit_policy]` MAY restrict scopes and constrain identities; it SHALL NOT restate the grammar or the signature.

#### Scenario: The binding declares no subject grammar

- **WHEN** `[commit_policy]` declares no `subject_pattern`
- **THEN** commit admission accepts `feat(cli)!: drop the legacy flag` and rejects `style: reformat`.

#### Scenario: A repository declares no commit policy

- **WHEN** a repository tracks no `[commit_policy]`
- **THEN** commit admission requires the shared grammar and a trusted SSH signature on every introduced commit
- **AND** ETHOS signs the commits it creates.

#### Scenario: A repository adds a type

- **WHEN** a repository commit policy declares its own `subject_pattern`, for example one that admits a `spec` or `style` type
- **THEN** the paradigm reports a restated commit grammar.

#### Scenario: A binding restates the signature

- **WHEN** `[commit_policy]` declares `signing_required` or `signing_format`, with any value
- **THEN** the paradigm reports a restated signature declaration and the repair deletes it
- **AND** commit admission still requires an SSH signature.

#### Scenario: A scope list is declared

- **WHEN** a repository declares the scopes `cli` and `relay`
- **THEN** commit admission rejects `fix(other): repair`.

### Requirement: Each repository keeps its lifecycle signer locally

ETHOS runs Git without global configuration, so every governed repository SHALL keep its lifecycle signer, `user.signingkey` with an optional `gpg.ssh.program`, and its trust anchor `gpg.ssh.allowedSignersFile` in local configuration. Formation SHALL write the creator's reviewed signer and anchor before it signs the initial commit. Status SHALL report the signer and SHALL block without it only in the roles that create lifecycle commits.

#### Scenario: A formed repository starts signed

- **WHEN** `ethos adopt --create` applies a reviewed plan that names the creator's signing key and trust anchor
- **THEN** the initial commit carries an SSH signature that the anchor verifies
- **AND** the new repository's local configuration holds the signer and the anchor.

#### Scenario: Formation names no signer

- **WHEN** a formation request names no signing key or no trust anchor
- **THEN** the preview refuses, and neither the target nor its candidate worktree exists.

#### Scenario: A lifecycle role has no signer

- **WHEN** status observes the accepted root, the candidate or a Work Lane whose local configuration has no valid signing key
- **THEN** commit enforcement is unready, and its next action is the exact local `user.signingkey` setting
- **AND** a detached checkout reports the same signer without blocking.

#### Scenario: The trust anchor is missing

- **WHEN** a repository has no local trust anchor
- **THEN** status and signer authorization name the same local `gpg.ssh.allowedSignersFile` setting.

#### Scenario: Signer authorization reads the lifecycle signer

- **WHEN** `ethos lane trust-commit-signer` authorizes a repository's configured signer
- **THEN** it reads the same local signing key and admits the same key types as lifecycle commit creation
- **AND** a key that commit creation refuses never enters the trust anchor, and the refusal names the local setting.

### Requirement: Branch roles and Work Lanes use the standard names

The repository paradigm SHALL fix the branch role names: release `main`, accepted `dev`, candidate `candidate/dev`, Work Lanes under `work/` and proposals under `proposal/`. ETHOS SHALL read nothing from `[branch_roles]`. A repository whose release branch follows its accepted branch SHALL declare `[release] mirror = "accepted_ff"` in `.ethos/release.toml`; otherwise the release mirror is independent. Every Work Lane worktree SHALL be a sibling at `<repository>-worktrees/<yyyymmdd>-<slug>/`.

#### Scenario: A review prefix differs

- **WHEN** a workspace declares `submit/` as its proposal prefix
- **THEN** the paradigm reports a legacy branch-role name
- **AND** ETHOS still uses `proposal/`.

#### Scenario: A workspace declares a standard name

- **WHEN** `[branch_roles]` declares `accepted_branch = "dev"`
- **THEN** the paradigm reports the declared name and names its removal.

#### Scenario: A Work Lane name already carries a date

- **WHEN** `ethos lane start 20261016-archive-relocation` runs
- **THEN** lane start refuses the name and names `archive-relocation` as the repair
- **AND** no Work Lane path repeats its date.

#### Scenario: A workspace declares the retired sibling-worktree setting

- **WHEN** `[branch_roles]` declares `canonical_sibling_worktrees = false`
- **THEN** `ethos lane start feature` still places the Work Lane at `<repository>-worktrees/<yyyymmdd>-feature/`
- **AND** the paradigm reports the setting and the repair deletes it.

#### Scenario: The release binding declares the mirror

- **WHEN** `.ethos/release.toml` declares `[release] mirror = "accepted_ff"`
- **THEN** accepted closeout, publication and ref admission read the standard names with an accepted fast-forward release mirror.

#### Scenario: A workspace still declares the mirror

- **WHEN** `[branch_roles]` declares `release_mirror = "accepted_ff"` and `.ethos/release.toml` declares no mirror
- **THEN** ETHOS reads an independent release mirror
- **AND** the paradigm reports both carriers and the repair moves the mirror to `[release] mirror`.

### Requirement: Accepted closeout renames legacy role refs

When the accepted root is bound to a ref that its committed table declares as a legacy accepted name, accepted closeout SHALL, in one ref transaction, create each standard role ref at the head of the legacy ref it replaces and delete that legacy ref, and SHALL bind every worktree on a renamed ref to its new name. Git admission SHALL refuse any other move of a legacy role ref.

#### Scenario: A repository adopted under legacy names

- **WHEN** the committed table names `accepted/train` and `candidate/train` and the accepted root is bound to `accepted/train`
- **THEN** closeout leaves `dev` and `candidate/dev` at the heads those refs had and removes the legacy refs
- **AND** the accepted and candidate worktrees are bound to `dev` and `candidate/dev`.

#### Scenario: A legacy role ref is moved directly

- **WHEN** a user runs `git branch -m accepted/train dev`
- **THEN** Git admission refuses the update with `legacy_role_ref_protected`.

### Requirement: Publication retires published legacy role refs

Publication retirement SHALL delete a published ref whose name the table committed at its remote head declares as a legacy accepted or candidate name only when that name has no current role and the accepted head, locally and on the peer, contains the remote head.

#### Scenario: A renamed accepted ref is still published

- **WHEN** a peer still carries `accepted/train` at a head whose table declares `accepted_branch = "accepted/train"` and the peer's `dev` contains that head
- **THEN** `ethos publish --retire --ref refs/heads/accepted/train` deletes it on each peer.

#### Scenario: The table at the head declares another name

- **WHEN** a peer carries `topic` at a head whose table declares no `topic` role name
- **THEN** publication retirement refuses `refs/heads/topic` as not a proposal.

### Requirement: Publication peers name their Git remotes after themselves

Each publication peer declared in `.ethos/release.toml` SHALL name its Git remote by its own peer id, so a GitLab peer `gitlab` uses the remote `gitlab` and a GitHub peer `github` uses `github`. No peer SHALL rely on the implicit remote `origin`.

#### Scenario: A peer keeps the implicit remote name

- **WHEN** the release binding declares the peer `gitlab` with `git_remote = "origin"`
- **THEN** the paradigm reports the peer and the rename to `gitlab`.

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

Markdown and YAML SHALL be formatted by Prettier, TOML by Taplo and Python by Ruff. Each formatter SHALL be bound through the repository's `fix` and `check` verbs, with configuration under `.config/checks/` declaring the common settings. Blank lines SHALL be what these formatters write for the parsed structure.

#### Scenario: Markdown is only linted

- **WHEN** a repository tracks Markdown and has no Prettier configuration in the configuration plane
- **THEN** the paradigm reports a missing Markdown formatter binding.

#### Scenario: Python is not formatted

- **WHEN** a repository tracks Python and has no Ruff configuration in the configuration plane
- **THEN** the paradigm reports a missing Python formatter binding.

#### Scenario: Blank lines pad a document

- **WHEN** a Markdown document separates two paragraphs with two blank lines
- **THEN** the `check` verb fails, and `fix` leaves one blank line.

#### Scenario: A formatter setting differs

- **WHEN** a repository's Prettier configuration sets `proseWrap` to `always`
- **THEN** the paradigm reports the carrier and the common setting it must declare.

#### Scenario: Only archived files use a carrier class

- **WHEN** a repository's only Python files sit under its immutable OpenSpec archive
- **THEN** the paradigm requires no Ruff binding.

### Requirement: Formatter inputs respect declared carrier ownership

A formatter's declared inputs SHALL exclude carriers that already have another declared owner, such as official OpenSpec artifacts. Those carriers SHALL keep their own owner and checks, and their Markdown layout SHALL still follow parsed structure.

#### Scenario: A carrier has an official owner

- **WHEN** a repository declares its OpenSpec artifacts official-owner-only
- **THEN** the Markdown formatter's inputs exclude them, their own checks still run, and the paradigm still reports their Markdown layout.

### Requirement: Text normalization is declared

Every governed repository SHALL keep `.editorconfig` and `.gitattributes` that select UTF-8, LF line endings and a final newline for tracked text. The last `.gitattributes` pattern for every file SHALL be `* text=auto eol=lf`; narrower patterns MAY mark specific carriers as binary or byte-exact.

#### Scenario: Line endings are undeclared

- **WHEN** a governed repository has no `.gitattributes`
- **THEN** the paradigm reports missing text normalization.

### Requirement: Configured formatters share one width

Every configured formatter SHALL use a line width of 100, including Prettier, Taplo and Ruff. A repository that configures Ruff SHALL also target Python 3.12.

#### Scenario: A formatter keeps its default width

- **WHEN** a repository's Ruff configuration sets or defaults to a line length of 88
- **THEN** the paradigm reports a non-common formatter width.

### Requirement: Python files stay within the common size ceiling

Every tracked Python file SHALL have at most 512 effective lines, counted without blank lines, comments and docstrings. The paradigm contract SHALL hold this ceiling and the value of the Markdown documentation ceiling, and a repository binding SHALL NOT restate, raise or lower either.

#### Scenario: A Python file outgrows the ceiling

- **WHEN** a governed repository tracks a Python file with 600 effective lines
- **THEN** the paradigm reports the file and the 512-line ceiling, whether or not the repository declares a size policy.

#### Scenario: A binding restates a ceiling

- **WHEN** `.ethos/rules.toml` declares `[quality.code_size]`
- **THEN** the paradigm reports a binding that restates a paradigm value.

### Requirement: JavaScript execution environments are declared and validated

A repository MAY declare in `.config/checks/eslint/policy.toml` that named tracked JavaScript files run in a browser, worker or service worker, with a stated reason. The native static gate SHALL admit only those standard global sets, for exactly those files, and SHALL NOT read repository ESLint configuration or inline directives.

#### Scenario: A browser callback is declared

- **WHEN** `render.mjs` evaluates `() => window.innerWidth` in a page and declares the browser set with a reason
- **THEN** the static gate passes for that file, and the same code in an undeclared file still fails.

#### Scenario: A declaration is not admissible

- **WHEN** a declaration names the node set, omits its reason or names an untracked file
- **THEN** the static gate fails closed.

### Requirement: Native Python behavior runs on a declared interpreter

When a Python project selects no mise toolchain, the native behavior gate SHALL run its tests on an interpreter its `requires-python` admits: the runtime interpreter when the declaration admits it, otherwise an installed interpreter that uv selects from the project's declaration.

#### Scenario: A project pins an older interpreter

- **WHEN** a project declares `requires-python = "==3.12.*"` and the runtime interpreter is 3.14
- **THEN** the gate does not pin the runtime interpreter, and uv selects an installed 3.12 interpreter.

### Requirement: Ecosystem modules lock their manifests

A repository that tracks `pyproject.toml` SHALL lock it with `uv.lock` and SHALL declare a Python lower bound of 3.12. A repository that declares npm dependencies SHALL lock them with `package-lock.json`, and a repository whose `go.mod` requires modules SHALL track `go.sum`. Tool and runtime versions remain repository-owned under the version policy.

#### Scenario: A Python manifest is unlocked

- **WHEN** a repository tracks `pyproject.toml` without `uv.lock`
- **THEN** the paradigm reports an unlocked Python module.

#### Scenario: A manifest without dependencies

- **WHEN** a repository's `package.json` declares only scripts, or its `go.mod` requires no modules
- **THEN** no lock is required for that module.

### Requirement: One locked toolchain owner exposes the common verbs

A repository SHALL select its toolchain through one locked owner: `.config/mise/` with locked resolution when it needs tools beyond its package manager, otherwise its package manager and lockfile. That owner SHALL expose `bootstrap`, `fix` and `check` as tasks.

#### Scenario: Toolchain configuration sits at the root

- **WHEN** a repository tracks a root `mise.toml`
- **THEN** the paradigm reports its canonical path `.config/mise/config.toml`.

#### Scenario: A verb is missing

- **WHEN** the toolchain owner exposes no `fix` task
- **THEN** the paradigm reports a missing common verb.

### Requirement: Repository orchestration is native

Repository-owned orchestration, including the common verbs, gates, CI steps and release steps, SHALL run through native tool commands or tasks of the toolchain owner, so that the same invocation works on every platform the repository supports. Each CI step SHALL invoke one such command unless a complete, current retention record names it as official installer or operating-system glue by exact text, owner, reason, platforms and evidence; review judges the evidence.

#### Scenario: A gate runs through a repository script

- **WHEN** a repository gate or CI step runs `tools/ci/run-secrets-scan.sh`
- **THEN** the paradigm reports repository-owned shell orchestration, with a native command or toolchain-owner task as the canonical repair.

#### Scenario: A CI step embeds a shell program

- **WHEN** a CI step contains a shell conditional or loop
- **THEN** the paradigm reports inline shell orchestration.

#### Scenario: Necessary glue is retained with a complete record

- **WHEN** the retention record names a CI step's Forge file, job and the digest of its exact text, with a catalogued class, owner, reason, platforms and evidence
- **THEN** the step conforms, whatever YAML quoting or block style carries that text.

#### Scenario: Retained glue changes

- **WHEN** the text of a recorded step changes, or a job that the record lists no longer carries it
- **THEN** the paradigm reports the step as inline shell and the record as stale.

#### Scenario: A record is incomplete

- **WHEN** a record lacks its evidence or names an uncatalogued class
- **THEN** the paradigm reports the record and admits no step through it.

#### Scenario: A gate cannot be retained

- **WHEN** a gate hands a shell program to an interpreter
- **THEN** the paradigm reports inline shell orchestration, whatever the retention record lists.

### Requirement: Tracked scripts are official generator output

A tracked shell or PowerShell script SHALL exist only as the output of an official generator that the packaged tool catalog names, with its generator version and output digest recorded for `check` to verify. Any other script class SHALL require an ETHOS Change that records its owner, necessity, scope and target-platform evidence.

#### Scenario: Official generator output is tracked

- **WHEN** a repository tracks the output of `mise generate bootstrap` with its recorded generator version and digest
- **THEN** it conforms.

#### Scenario: A hand-written script is tracked

- **WHEN** a repository tracks a hand-written `build.sh` that no catalogued generator produces
- **THEN** the paradigm reports an unadmitted script.

### Requirement: CI for several Forges is one model

A repository that runs CI on more than one Forge SHALL define its pipelines once as a CUE model under `.config/ci/` and generate each Forge file from that model. `check` SHALL fail when a generated Forge file differs from the model.

#### Scenario: Two Forge files are maintained by hand

- **WHEN** a repository tracks `.gitlab-ci.yml` and `.github/workflows/` without a model under `.config/ci/`
- **THEN** the paradigm reports an unmodeled multi-Forge pipeline.

#### Scenario: One Forge needs no model

- **WHEN** a repository runs CI only on GitLab
- **THEN** no pipeline model is required.

### Requirement: Repository-authored names use lowercase kebab-case

Repository-authored file and directory names SHALL use lowercase kebab-case, except where an ecosystem or tool fixes the name, such as Python modules, Go packages, entry documents and tool-required basenames. A leading `.` or `_` marker and dot-separated suffixes are not word separators, and names inside immutable record roots keep their captured form.

#### Scenario: A rule file uses snake_case

- **WHEN** a repository tracks `rules/module_layout.md`
- **THEN** the paradigm reports a non-standard name with its kebab-case form.

#### Scenario: An ecosystem or tool fixes the name

- **WHEN** a repository tracks `src/sample_package/module_name.py`, `.github/PULL_REQUEST_TEMPLATE.md` and `docs/_meta/taxonomy.toml`
- **THEN** no name is reported.

#### Scenario: A new snake_case file is requested

- **WHEN** a Work Lane requests prewrite admission for a new `rules/module_layout.md`
- **THEN** admission refuses the path and names `rules/module-layout.md`.

### Requirement: Language tags and received names keep their form

A dot-separated name segment MAY be a BCP 47 language tag in its canonical case. A path that the repository's Git attributes mark `linguist-vendored` or `linguist-generated` is received rather than authored and SHALL keep its name, and so SHALL a directory that holds only such paths.

#### Scenario: A localized carrier names its language

- **WHEN** a repository tracks `media/captions.zh-CN.vtt` and `media/transcript.zh-Hans-CN.md`
- **THEN** no name is reported
- **AND** `media/captions.ZH-CN.vtt` is reported, because its language subtag is not lowercase.

#### Scenario: A vendored font keeps its upstream name

- **WHEN** the repository's `.gitattributes` marks `assets/fonts/**` as `linguist-vendored` and the repository tracks `assets/fonts/NotoSansCJKsc-Bold.otf`
- **THEN** no name is reported, and prewrite admits a new file there under its upstream name
- **AND** without that attribute the same name is reported.

### Requirement: Paradigm conformance is a blocking verdict

The repository audit SHALL report every paradigm gap with its carrier, the violated obligation and the canonical repair. While any gap remains, prove, land and publish SHALL be blocked. Prewrite admission SHALL refuse a write that would create a path the paradigm rejects.

#### Scenario: A repository conforms

- **WHEN** a governed repository has no paradigm gap
- **THEN** the audit reports a passing paradigm report and does not block.

#### Scenario: A non-conforming path is requested

- **WHEN** a Work Lane requests prewrite admission for a new root `pytest.ini`
- **THEN** admission refuses the path and names `.config/checks/pytest/pytest.toml`.

### Requirement: Deterministic paradigm gaps carry a native repair

ETHOS SHALL derive a repair for every paradigm gap whose fix follows from the gap's obligation and the carrier's current text alone, and SHALL apply it only inside a Work Lane after exact-path prewrite admission. Each new obligation SHALL ship with its repair or SHALL declare its gaps report-only. A gap that needs judgment, such as a Python file over the size ceiling, a changelog, a version source or a decision record rename, SHALL stay report-only. Repeating a repair SHALL change nothing.

#### Scenario: A repair is previewed

- **WHEN** a repository lacks `.editorconfig` and wraps a document's front matter in `<!--` and `-->`
- **THEN** the repair preview names both carriers and their repaired text, and writes nothing.

#### Scenario: A repair is applied in a Work Lane

- **WHEN** the repair is applied in a Work Lane whose prewrite admits every repaired path
- **THEN** each carrier holds its repaired text and the paradigm report no longer names those gaps.

#### Scenario: Prewrite refuses a repaired path

- **WHEN** the repair is applied where prewrite admission refuses a repaired path
- **THEN** the repair writes nothing and reports the admission gaps.

#### Scenario: A repair is repeated

- **WHEN** the repair is applied a second time to the repaired tree
- **THEN** it plans no edit.

#### Scenario: A gap needs judgment

- **WHEN** a tracked Python file exceeds the size ceiling
- **THEN** the repair reports the gap with its canonical repair and plans no edit for it.

#### Scenario: A remote follows a peer rename

- **WHEN** the `gitlab` peer declares `git_remote = "origin"`
- **THEN** the repair sets `git_remote = "gitlab"` and names `git remote rename origin gitlab` as the next action without running it.

#### Scenario: A restated paradigm value is deleted

- **WHEN** a workspace binding declares a standard branch-role name at the name the paradigm fixes, or a commit subject pattern equal to the shared grammar
- **THEN** the repair deletes that field and keeps every comment and other key, while a legacy role name or a repository's own grammar stays report-only.

### Requirement: Markdown layout follows parsed structure

Every authored Markdown document SHALL separate adjacent blocks and leading front matter with one blank line, keep reference definitions together, keep a one-block list item tight with the next item and separate any other item's blocks and its next item with one blank line, without repeated blank lines or edge padding. Quotes, tables, literal blocks and the node after a formatter-ignore comment keep their bytes; received documents and immutable roots are exempt.

#### Scenario: A blank line follows a one-block list item

- **WHEN** a Changelog list leaves a blank line after a one-paragraph item
- **THEN** the paradigm reports the document's Markdown layout, and `ethos lane repair-paradigm --apply` removes only that blank line.

#### Scenario: A heading touches its text

- **WHEN** a main spec carries `## Purpose` directly followed by its paragraph
- **THEN** the paradigm reports the document, and the repair inserts one blank line.

#### Scenario: A multi-block item touches the next item

- **WHEN** a list item's two paragraphs are separated but the next item follows without a blank line
- **THEN** the repair separates them with one blank line.

#### Scenario: A code block holds blank lines

- **WHEN** a fenced code block holds two consecutive blank lines
- **THEN** the paradigm reports no Markdown layout gap.

#### Scenario: A received transcript keeps its bytes

- **WHEN** Git attributes mark a verbatim transcript `linguist-vendored`
- **THEN** the paradigm does not lay it out.

#### Scenario: A repair would change the structure

- **WHEN** dropping blank lines before a document's YAML-like block would turn it into front matter
- **THEN** the gap stays report-only.
