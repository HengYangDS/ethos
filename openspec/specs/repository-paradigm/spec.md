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

Every governed repository SHALL keep `AGENTS.md`, `CONTRIBUTING.md` and `README.md` at its root.
`AGENTS.md` SHALL be the only agent entry; repository-local Skills SHALL live under
`.agents/skills/`.

#### Scenario: A repository lacks the agent entry

- **WHEN** a governed repository has no root `AGENTS.md`
- **THEN** the paradigm reports a missing entry document.

#### Scenario: A repository lacks the contributor guide

- **WHEN** a governed repository that publishes to two forges has no root `CONTRIBUTING.md`
- **THEN** the paradigm reports a missing entry document

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

When a repository configures secret scanning or Ruff, native pre-commit admission SHALL use the
configuration at its canonical `.config/` path. Configuration found anywhere else SHALL be reported
as a gap and SHALL NOT silently disable the check. When a repository configures no Ruff,
pre-commit admission SHALL check staged Python with the shipped Ruff settings.

#### Scenario: Secret scanning configuration moves

- **WHEN** Gitleaks configuration exists only at `.config/checks/gitleaks/gitleaks.toml`
- **THEN** pre-commit admission scans the staged content with that configuration.

#### Scenario: A repository keeps no Ruff configuration

- **WHEN** a repository tracks no Ruff configuration and stages a Python file that the shipped Ruff
  settings would reformat
- **THEN** pre-commit admission refuses the commit with `pre_commit_python_format_failed` for that
  path.

### Requirement: The binding uses only ETHOS-defined files

The tracked `.ethos/` binding SHALL contain only `profile.toml`, `workspace.toml`, `release.toml` and `rules.toml`. A repository SHALL declare its own proof gates in `profile.toml` or in the gate registry file its profile names, and receives the shared obligations its facts select. `workspace.toml` SHALL declare only `[commit_policy]`, and a repository that declares none SHALL NOT track it.

#### Scenario: A legacy binding file is tracked

- **WHEN** `.ethos/assistants.toml`, `.ethos/project.toml` or `.ethos/gates.toml` is tracked
- **THEN** the paradigm reports a binding file outside the ETHOS schema set.

#### Scenario: A profile names its own gate registry

- **WHEN** a profile names a tracked registry file outside `.ethos/`, such as `system/repository-gates.toml`
- **THEN** the repository's proof gates are that file's gates plus the shared obligations its facts select
- **AND** the registry's path does not change which shared obligations apply

#### Scenario: A workspace declares a table no reader consults

- **WHEN** `.ethos/workspace.toml` declares `[[package]]`
- **THEN** the paradigm reports the table and the repair deletes it.

#### Scenario: A workspace binding declares nothing else

- **WHEN** `.ethos/workspace.toml` declares only `[branch_roles]` with `release_mirror = "independent"`
- **THEN** the repair deletes `.ethos/workspace.toml`.

### Requirement: OpenSpec carries the common rules

Every governed repository that tracks OpenSpec artifacts SHALL select the `spec-driven` schema in
`openspec/config.yaml`, and each artifact's rules SHALL begin with the common rules that the
paradigm contract holds. Repository-specific rules SHALL only follow those common rules. The
paradigm contract's OpenSpec table SHALL also declare `rebuild.toml` as the one Change-local record
that ETHOS reads in a Change's directory beside its official artifacts.

#### Scenario: The common task rule is missing

- **WHEN** a repository configuration omits the common tasks rule
- **THEN** the paradigm reports the missing common rule.

#### Scenario: Repository rules come before the common rules

- **WHEN** a configuration lists only its own proposal rule, in a flow sequence
- **THEN** the repair rewrites the proposal rules as a block sequence that begins with the common
  rules and keeps the repository's rule after them, leaving every other key and comment unchanged.

#### Scenario: A repository selects its own schema

- **WHEN** a configuration selects a schema other than `spec-driven`
- **THEN** the paradigm reports the schema, and the repair leaves that gap report-only.

#### Scenario: A repository tracks no OpenSpec artifact

- **WHEN** a repository tracks no path under `openspec/`
- **THEN** the paradigm reports no OpenSpec gap.

#### Scenario: A Change carries a rebuild record

- **WHEN** a Change's directory holds `rebuild.toml`, whose entries are digests and no markers
- **THEN** ETHOS reads it as that Change's declared record
- **AND** the Change lands and archives without `record_marker_unpaired`

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

When the accepted root is bound to a ref that its committed table declares as a legacy accepted
name, accepted closeout SHALL, in one ref transaction, create each standard role ref at the head of
the legacy ref it replaces and delete that legacy ref, and SHALL bind each worktree on a renamed ref
to its new name by compare-and-swap in an authorized apply, on Git 2.46 or later. Git admission
SHALL refuse any other move of a legacy role ref, except deleting one whose successor holds its
commit.

#### Scenario: A repository adopted under legacy names

- **WHEN** the committed table names `accepted/train` and `candidate/train` and the accepted root is bound to `accepted/train`
- **THEN** closeout leaves `dev` and `candidate/dev` at the heads those refs had and removes the legacy refs
- **AND** the accepted and candidate worktrees are bound to `dev` and `candidate/dev`.

#### Scenario: A legacy role ref is moved directly

- **WHEN** a user runs `git branch -m accepted/train dev`
- **THEN** Git admission refuses the update with `legacy_role_ref_protected`.

#### Scenario: A legacy role ref duplicates its successor

- **WHEN** the committed table names `integration/dev` as the legacy candidate name, and `candidate/dev` holds the same commit as `integration/dev`
- **THEN** the absorbed-ref retirement deletes `integration/dev`, and Git admission admits that deletion
- **AND** no other legacy role ref is renamed or moved.

#### Scenario: An interrupted binding is previewed

- **WHEN** the refs are renamed but the accepted and candidate worktrees still name `accepted/train`
  and `candidate/train`
- **THEN** `ethos land --closeout --json` reports `branch_role_rebinding_pending` for both and
  changes no `HEAD`
- **AND** its next action is the closeout apply with `--expect-head` set to the head of `dev`

#### Scenario: A refused apply binds nothing

- **WHEN** that apply lacks `--authorize` or names another head
- **THEN** it blocks and every `HEAD` still names its legacy ref

#### Scenario: A worktree moves after detection

- **WHEN** a worktree's `HEAD` no longer names its legacy ref when the binder writes
- **THEN** that worktree keeps its `HEAD` and the apply blocks with
  `branch_role_worktree_binding_stale`

#### Scenario: Git lacks symbolic-ref transactions

- **WHEN** Git refuses the `symref-verify` probe of `git update-ref --stdin`
- **THEN** the rename, retained-topic and rebinding applies refuse with
  `branch_role_rename_git_unsupported` and no ref or `HEAD` moves

### Requirement: Publication retires published legacy role refs

Publication retirement SHALL delete a published ref whose name the table committed at its remote head declares as a legacy accepted or candidate name only when that name has no current role and the accepted head, locally and on the peer, contains the remote head.

#### Scenario: A renamed accepted ref is still published

- **WHEN** a peer still carries `accepted/train` at a head whose table declares `accepted_branch = "accepted/train"` and the peer's `dev` contains that head
- **THEN** `ethos publish --retire --ref refs/heads/accepted/train` deletes it on each peer.

#### Scenario: The table at the head declares another name

- **WHEN** a peer carries `topic` at a head whose table declares no `topic` role name
- **THEN** publication retirement refuses `refs/heads/topic` as not a proposal.

### Requirement: Publication peers name their Git remotes after themselves

With two or more publication peers declared in `.ethos/release.toml`, each SHALL name its Git remote
by its own peer id, so a GitLab peer `gitlab` uses the remote `gitlab` and a GitHub peer `github`
uses `github`, and none SHALL use the clone remote name. A sole publication peer MAY keep the clone
remote name, which the repository paradigm declares as Git's default `origin`, the name `git clone`
gives the one remote it clones from.

#### Scenario: A peer keeps the implicit remote name

- **WHEN** the release binding declares the peers `gitlab` and `github`, and `gitlab` has
  `git_remote = "origin"`
- **THEN** the paradigm reports the peer and the rename to `gitlab`.

#### Scenario: A sole peer keeps the clone's name

- **WHEN** the release binding declares only the peer `gitlab`, with `git_remote = "origin"`
- **THEN** the paradigm reports no remote gap

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

### Requirement: Formatter inputs respect declared carrier ownership

A formatter's declared inputs SHALL exclude carriers that already have another declared owner, such as official OpenSpec artifacts. Those carriers SHALL keep their own owner and checks, layout included.

#### Scenario: A carrier has an official owner

- **WHEN** a repository declares its OpenSpec artifacts official-owner-only
- **THEN** the Markdown formatter's inputs exclude them, their own checks still run, and no other rule lays them out.

### Requirement: Text normalization is declared

Every governed repository SHALL keep `.editorconfig` and `.gitattributes` that select UTF-8, LF line endings and a final newline for tracked text. The last `.gitattributes` pattern for every file SHALL be `* text=auto eol=lf`; narrower patterns MAY mark specific carriers as binary or byte-exact, but SHALL NOT give a tracked file CRLF or host-dependent line endings under the attributes that Git resolves.

#### Scenario: Line endings are undeclared

- **WHEN** a governed repository has no `.gitattributes`
- **THEN** the paradigm reports missing text normalization.

#### Scenario: A narrower pattern selects another line ending

- **WHEN** a conforming `.gitattributes` is followed by `run.cmd eol=crlf`, or a nested `.gitattributes` gives `docs/*.md` no `eol`
- **THEN** the paradigm reports each file whose effective attributes select that line ending, with a repair that drops the override or marks the file `-text`
- **AND** a file marked `-text`, `binary` or byte-exact keeps its bytes without a gap.

### Requirement: Configured formatters share one width

Every configured formatter SHALL use a line width of 100, including Prettier, Taplo and Ruff. A repository that configures Ruff SHALL also target Python 3.12.

#### Scenario: A formatter keeps its default width

- **WHEN** a repository's Ruff configuration sets or defaults to a line length of 88
- **THEN** the paradigm reports a non-common formatter width.

### Requirement: Code files stay within the common size ceiling

Every tracked file of a registry language SHALL have at most `code_effective_lines` effective lines,
the lines that hold a token that is not whitespace, a comment or documentation, unless Git
attributes mark it vendored or generated or it is a declared byte-bound carrier. The contract SHALL
hold a default of 500 and a bound of 1000 for both per-file ceilings. A binding MAY declare one
whole-tree value in `.ethos/rules.toml` `[paradigm.size]`; an invalid one SHALL leave the default in
force.

#### Scenario: A Python file outgrows the ceiling

- **WHEN** a governed repository that declares no code ceiling tracks a Python file with 501
  effective lines
- **THEN** the paradigm reports the file and the 500-line ceiling.

#### Scenario: A file in another language outgrows the ceiling

- **WHEN** a governed repository that declares no code ceiling tracks a Go, Rust or JavaScript file
  with 501 effective lines
- **THEN** the paradigm reports the file and the 500-line ceiling.

#### Scenario: Comments and documentation do not count

- **WHEN** a tracked Rust file holds 450 lines of code, 20 attribute lines and 100 lines of `///`
  documentation and `//` comments
- **THEN** it has 470 effective lines and passes the default ceiling.

#### Scenario: The registry decides what is code

- **WHEN** a repository tracks TOML, JSON, YAML, CUE and Markdown files with 800 lines each
- **THEN** the code ceiling measures none of them.

#### Scenario: A received file is not measured

- **WHEN** the repository's `.gitattributes` marks a tracked JavaScript file with 900 effective
  lines `linguist-generated`
- **THEN** the paradigm reports no code size gap for it.

#### Scenario: A byte-bound carrier is not measured

- **WHEN** the repository's format selection declares a tracked JavaScript file with 900 effective
  lines an immutable carrier whose bytes one of its proof gates verifies
- **THEN** the paradigm reports no code size gap for it
- **AND** an invalid carrier declaration leaves the file measured.

#### Scenario: A repository declares a lower ceiling

- **WHEN** `[paradigm.size]` declares `code_effective_lines = 400` and a tracked Go file has 450
  effective lines
- **THEN** the paradigm reports the file and the 400-line ceiling.

#### Scenario: A repository declares a higher ceiling with its reason

- **WHEN** `[paradigm.size]` declares `code_effective_lines = 700` and `[paradigm.size.reasons]`
  states why
- **THEN** a tracked code file with 650 effective lines passes
- **AND** the paradigm report lists the declared value and its reason as a deviation from the
  default.

#### Scenario: An invalid declaration leaves the default in force

- **WHEN** `[paradigm.size]` declares `code_effective_lines = 700` without a reason, declares
  `1200`, declares a value that is not a positive integer or names an unknown key
- **THEN** the paradigm reports the declaration
- **AND** a tracked code file with 650 effective lines is reported against the 500-line ceiling.

#### Scenario: A binding restates a ceiling

- **WHEN** `[paradigm.size]` declares `code_effective_lines = 500`
- **THEN** the paradigm reports a binding that restates a paradigm value.

#### Scenario: A binding declares a retired key

- **WHEN** `[paradigm.size]` declares `python_effective_lines` or `markdown_nonblank_lines`
- **THEN** the paradigm reports the declaration with the repair to rename it `code_effective_lines`
  or `document_nonblank_lines`
- **AND** the default stays in force.

#### Scenario: A binding keeps the retired table

- **WHEN** `.ethos/rules.toml` declares `[quality.code_size]`
- **THEN** the paradigm reports the table with the repair to declare `[paradigm.size]`.

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

A repository SHALL select its toolchain through one locked owner: `.config/mise/` with locked
resolution when it needs tools beyond its package manager, otherwise its package manager and
lockfile. That owner SHALL expose `bootstrap`, `fix` and `check` as tasks. A mise configuration that
selects no tool needs no lock, since mise writes none for it.

#### Scenario: Toolchain configuration sits at the root

- **WHEN** a repository tracks a root `mise.toml`
- **THEN** the paradigm reports its canonical path `.config/mise/config.toml`.

#### Scenario: A verb is missing

- **WHEN** the toolchain owner exposes no `fix` task
- **THEN** the paradigm reports a missing common verb.

#### Scenario: A configuration selects no tool

- **WHEN** `.config/mise/config.toml` sets `locked = true` and declares the three verbs but selects
  no tool, through `[tools]`, idiomatic version files or `.tool-versions`
- **THEN** the paradigm requires no `.config/mise/mise.lock`
- **AND** a configuration that selects a tool still requires the tracked lock.

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

Repository-authored file and directory names SHALL use lowercase kebab-case, except where an
ecosystem or tool fixes the name: the module files of a registry language whose toolchain fixes
module names, such as Python, Go and Rust, and the directories that hold them, entry documents and
tool-required basenames. A leading `.` or `_` marker and dot-separated suffixes are not word
separators, and names inside immutable record roots keep their captured form.

#### Scenario: A rule file uses snake_case

- **WHEN** a repository tracks `rules/module_layout.md`
- **THEN** the paradigm reports a non-standard name with its kebab-case form.

#### Scenario: An ecosystem or tool fixes the name

- **WHEN** a repository tracks `src/sample_package/module_name.py`,
  `crates/channel_solver/src/flow_graph.rs`, `.github/PULL_REQUEST_TEMPLATE.md` and
  `docs/_meta/taxonomy.toml`
- **THEN** no name is reported.

#### Scenario: A new snake_case file is requested

- **WHEN** a Work Lane requests prewrite admission for a new `rules/module_layout.md`
- **THEN** admission refuses the path and names `rules/module-layout.md`.

### Requirement: Language tags and received names keep their form

A dot-separated name segment MAY be a BCP 47 language tag in its canonical case. A path that the repository's Git attributes mark `linguist-vendored` or `linguist-generated` is received rather than authored and SHALL keep its name, and so SHALL a directory that holds only such paths. The repair for a name outside kebab-case SHALL name both ways out: renaming it to its kebab-case form, and marking it received when a third party or a generator authored it.

#### Scenario: A localized carrier names its language

- **WHEN** a repository tracks `media/captions.zh-CN.vtt` and `media/transcript.zh-Hans-CN.md`
- **THEN** no name is reported
- **AND** `media/captions.ZH-CN.vtt` is reported, because its language subtag is not lowercase.

#### Scenario: A vendored font keeps its upstream name

- **WHEN** the repository's `.gitattributes` marks `assets/fonts/**` as `linguist-vendored` and the repository tracks `assets/fonts/NotoSansCJKsc-Bold.otf`
- **THEN** no name is reported, and prewrite admits a new file there under its upstream name
- **AND** without that attribute the same name is reported, with a repair that names its kebab-case form and the `linguist-vendored` or `linguist-generated` marking.

### Requirement: Paradigm conformance is a blocking verdict

The repository audit SHALL report every paradigm gap with its carrier, the violated obligation and the canonical repair. While any gap remains, prove, land and publish SHALL be blocked. Prewrite admission SHALL refuse a write that would create a path the paradigm rejects. A path that the index or HEAD tracks is not created by its write, so prewrite SHALL admit its deletion.

#### Scenario: A repository conforms

- **WHEN** a governed repository has no paradigm gap
- **THEN** the audit reports a passing paradigm report and does not block.

#### Scenario: A non-conforming path is requested

- **WHEN** a Work Lane requests prewrite admission for a new root `pytest.ini`
- **THEN** admission refuses the path and names `.config/checks/pytest/pytest.toml`.

#### Scenario: A tracked non-conforming carrier is retired

- **WHEN** a Work Lane requests prewrite admission for a tracked root `pytest.ini` that it has
  deleted from the worktree, staged or not
- **THEN** admission reports no paradigm gap for the path.

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

### Requirement: A license grant is a recognized standard text

A governed repository that tracks a root `LICENSE` SHALL keep in it the standard text of one license whose SPDX template the paradigm contract pins by digest, matched as the SPDX matching guidelines describe, unless its package metadata names the license by a `LicenseRef-` identifier. A copyright notice that the template requires SHALL name its holder, and only the template's own title MAY precede it. Which license a repository grants remains its own choice.

#### Scenario: A grant departs from its license

- **WHEN** a repository's `LICENSE` edits or retitles the MIT text, or keeps the template placeholder instead of a copyright holder
- **THEN** the paradigm reports the grant, naming the recognized licenses.

#### Scenario: A license outside the SPDX list is declared

- **WHEN** a repository's `LICENSE` holds its own proprietary terms and its `pyproject.toml` declares `LicenseRef-Proprietary`
- **THEN** the grant conforms, and a `package.json` that declares `MIT` is reported.

### Requirement: A license grant is linked and consistently declared

A repository that tracks a root `LICENSE` SHALL link it from its `README.md`. Every root `package.json`, `package-lock.json` or `pyproject.toml` that declares a license SHALL declare the same SPDX identifier, and a repository SHALL NOT need a package for these checks.

#### Scenario: Metadata names another license

- **WHEN** a repository grants MIT and its `package.json` declares `Apache-2.0`
- **THEN** the paradigm reports the manifest, while a `pyproject.toml` that declares `MIT` conforms.

#### Scenario: A grant stands without a package

- **WHEN** a documentation repository tracks the standard MIT text and its `README.md` links it, with no package manifest
- **THEN** no license gap is reported
- **AND** removing the link reports the public entry.

### Requirement: Link observation distinguishes authored candidates from committed proof

Shared host link observation SHALL check current authored Markdown, including tracked edits and nonignored new files, without changing source, index or HEAD. The shared source owner SHALL preserve bounded regular reads, internal alias safety, ownership exclusions and freshness. Committed proof and provenance SHALL keep exact committed membership and bytes; candidate results SHALL NOT claim committed source-tree coverage.

#### Scenario: Pending authored Markdown has a local link

- **WHEN** a tracked edit or nonignored new Markdown file links to a present candidate member or a missing target
- **THEN** ordinary host observation checks that input and reports its actual link outcome
- **AND** exact-HEAD execution refuses the dirty source instead of issuing proof.

#### Scenario: Candidate inputs change during native execution

- **WHEN** observed source bytes, aliases, input membership or HEAD change while the checker runs
- **THEN** the observation is unproved rather than a passing check of the final input
- **AND** ignored incidental files never qualify as candidate delivery targets.

### Requirement: Authored text is valid text

Authored text SHALL be complete UTF-8 without NUL. One shared judgement SHALL validate the complete authored-text selection before formatter narrowing. Source-format, Markdown lint and prose SHALL use it; the format fix SHALL refuse malformed bytes without writing. Native checkout attributes SHALL NOT decide text validity. Binary, generated-projection, dependency and archived evidence bytes SHALL retain their existing verification owner.

#### Scenario: Authored Markdown holds a NUL byte

- **WHEN** an authored Markdown file contains a NUL byte, including after Git's initial binary-detection window
- **THEN** source-format, Markdown lint and prose each report `authored_text_binary` for that file, and `lane format --apply` refuses without writing.

#### Scenario: An authored carrier has malformed UTF-8

- **WHEN** a declared plain-text, INI, vocabulary or canonical extensionless carrier contains malformed UTF-8
- **THEN** source-format reports `authored_text_encoding` with its path before preparing any formatter postimage, and the format fix leaves all source bytes and the index unchanged.

#### Scenario: A valid document is marked -text

- **WHEN** `.gitattributes` marks a valid UTF-8 Markdown document `-text`
- **THEN** none of the three checks reports it as binary, and it passes.

#### Scenario: Non-authored bytes retain their owner

- **WHEN** binary, generated-projection, dependency or archived evidence bytes are present
- **THEN** their existing owner controls verification and the authored-text judgement does not reinterpret or rewrite them.

### Requirement: Text formatting uses the shipped common formatters

Markdown and YAML SHALL be formatted by Prettier, TOML by Taplo and Python by Ruff through the
repository's `fix` and `check` verbs. ETHOS SHALL ship their common settings; a repository's own
configuration under `.config/checks/` SHALL be optional and SHALL keep those settings. Blank lines
SHALL be what the formatters write, except where the Markdown list rule decides them.

#### Scenario: No local formatter configuration

- **WHEN** a repository tracks Markdown, TOML and Python and keeps no Prettier, Taplo or Ruff
  configuration in the configuration plane
- **THEN** the paradigm reports no formatter gap and the formatters run on the shipped settings

#### Scenario: Blank lines pad a document

- **WHEN** a Markdown document separates two paragraphs with two blank lines
- **THEN** the `check` verb fails, and `fix` leaves one blank line.

#### Scenario: The formatter keeps a loose list

- **WHEN** a Markdown list separates its one-paragraph items with blank lines
- **THEN** Prettier alone keeps the lines, and the Markdown list rule refuses the list and removes
  them.

#### Scenario: A formatter setting differs

- **WHEN** a repository's Prettier configuration sets `proseWrap` to `always`
- **THEN** the paradigm reports the carrier and the common setting it must declare.

#### Scenario: Only archived files use a carrier class

- **WHEN** a repository's only Python files sit under its immutable OpenSpec archive and it keeps a
  Ruff configuration that differs from the common settings
- **THEN** the paradigm reports no Ruff setting gap.

### Requirement: Released products grant a license

A repository that tags releases SHALL keep its license grant in a root `LICENSE`, beside `VERSION`
and `CHANGELOG.md`. A repository that tags no release MAY omit it.

#### Scenario: A releasing repository has no license grant

- **WHEN** the release binding declares release tags and the repository tracks no root `LICENSE`
- **THEN** the paradigm reports the missing license grant

#### Scenario: A repository that never releases has no license grant

- **WHEN** a governed repository declares no release tags and tracks no root `LICENSE`
- **THEN** the paradigm reports no license gap

### Requirement: Tunable values are declared parameters

Every value ETHOS applies that a repository may change SHALL be declared once in the paradigm with
its default, unit and bound. A binding MAY declare its own value in `rules.toml`
`[paradigm.<group>]`: a lower value applies, and a higher one within the bound with a reason in
`[paradigm.<group>.reasons]`; a floor row applies only higher values, without a reason. Any other
declaration SHALL be a gap that leaves the default in force. Product code SHALL read each value
through the declaration.

#### Scenario: A repository needs a longer gate budget

- **WHEN** a binding declares `timeout.gate_seconds = 1200` with a reason
- **THEN** each of the repository's gates without its own timeout runs under 1,200 seconds
- **AND** its proofs list that value with the reason.

#### Scenario: A higher value has no reason or exceeds the bound

- **WHEN** a binding declares a higher `timeout` value without a reason, or one beyond its bound
- **THEN** the paradigm reports the declaration and the default stays in force.

#### Scenario: A lower value

- **WHEN** a binding declares a lower `timeout.git_seconds`
- **THEN** it applies without a reason.

#### Scenario: Product code restates a timeout

- **WHEN** product code binds a numeric literal to a wait, as a timeout argument or a duration
  constant
- **THEN** ETHOS's architecture check reports the file and line.

#### Scenario: A retention floor

- **WHEN** a binding declares a higher `retention.record_seconds` without a reason, or a lower one
- **THEN** the higher value applies, and the lower one is a gap that leaves the default in force

### Requirement: Declared names and carrier paths have one source

The paradigm SHALL be the one source of the branch role names, the binding root and files, the
version source and the changelog. Product code SHALL build each from the declaration, and an
architecture check SHALL report any other string constant in `src/` or `tools/`, docstrings aside,
that contains a binding carrier path or file name or equals the version source, the changelog or a
multi-segment branch role value.

#### Scenario: Product code restates a binding carrier

- **WHEN** a product module passes `.ethos/release.toml` as a string constant
- **THEN** the architecture check reports the file and line.

#### Scenario: A gap code names a binding carrier

- **WHEN** a gap code names `.ethos/profile.toml`
- **THEN** its value is built from the declaration and is unchanged.

#### Scenario: A branch role is read without arguments

- **WHEN** a branch role policy is built without arguments
- **THEN** it carries the names that the paradigm's `[branch]` table declares.

### Requirement: Tracked content and commit and tag messages carry no private-class network address

The paradigm SHALL declare one pattern of private-class network addresses: RFC 1918 and RFC 4193
literals, and names under `.local`, `.internal`, `.lan` or `.home.arpa` in host position. Commit and
tag admission SHALL refuse a message that matches it, and ETHOS's content scans SHALL refuse a match
in tracked or staged content. No scan SHALL read history, and no gap SHALL repeat the address.

#### Scenario: A commit message names a private forge

- **WHEN** a commit message body carries a remote URL whose host is an RFC 1918 address with a port
- **THEN** commit admission refuses the commit with `commit_message_private_address`
- **AND** the gap does not repeat the address.

#### Scenario: Documentation forms and the public identity pass

- **WHEN** content or a message uses `192.0.2.1`, `2001:db8::1`, `example.invalid` or the public
  distribution identity `github.com/HengYangDS/<repo>`
- **THEN** the content scans and message admission pass.

#### Scenario: A merge message names only a project path

- **WHEN** a merge message ends with `See merge request <group>/<project>!7` and names no host
- **THEN** commit admission accepts it, because the pattern judges address structure, not names.

#### Scenario: A tag message names a private host

- **WHEN** a signed tag's message names a host under `.internal` with a port
- **THEN** tag admission refuses the tag with `release_tag_message_private_address`.

#### Scenario: Only history holds an address

- **WHEN** a repository's history holds a private-class address and neither its tracked files nor
  its staged change do
- **THEN** both content scans pass.

#### Scenario: A code attribute shares a private suffix

- **WHEN** content names `threading.local` or `version.local` outside host position
- **THEN** the content scans pass.

#### Scenario: An immutable record is redacted

- **WHEN** a record replaces a private literal with a peer marker
  `<32 lowercase hex>.<32 lowercase hex>.private-peer.invalid`
- **THEN** the content scans pass.

#### Scenario: Loopback and link-local literals pass

- **WHEN** content or a message names a loopback or link-local literal, such as a port bound to the
  loopback interface
- **THEN** the content scans and message admission pass, because such a literal discloses no peer

### Requirement: Retired publication fields are repaired, never ignored

The paradigm SHALL report `forge_repository`, `local_verification_command` and
`local_installation_command` in the publication declaration as retired. The report SHALL block
prove, land and publish, and SHALL NOT block `status`, `lane start`, prewrite,
`lane repair-paradigm` or commit. The repair SHALL derive from the carrier text alone, SHALL remove
the fields without echoing their values, and SHALL admit a declaration left without publication
fields as zero peers.

#### Scenario: A declaration still carries a retired field

- **WHEN** a repository's `release.toml` carries `forge_repository` or a local command field
- **THEN** the paradigm reports the retired field and names `ethos lane repair-paradigm --apply`
- **AND** `status` and prewrite still run

#### Scenario: The repair removes the fields without echoing values

- **WHEN** `lane repair-paradigm --apply` removes a retired `forge_repository`
- **THEN** its report names the field and the peer and never the value
- **AND** a second run changes nothing

### Requirement: The per-file code ceiling is admitted at commit time

`pre-commit` SHALL measure each staged authored regular file of a registered language on its index
blob with the same measure and the same resolved ceiling as the paradigm report, and SHALL refuse
the commit when a file exceeds the ceiling, naming the file, its effective lines and the ceiling, or
when its blob cannot be measured. The paradigm report SHALL keep its whole-tree check.

#### Scenario: A staged file exceeds the ceiling

- **WHEN** a commit stages a source file whose index blob exceeds the per-file code ceiling
- **THEN** `pre-commit` refuses with `pre_commit_code_size_exceeded:<path>:<lines>><ceiling>`

#### Scenario: Only the worktree copy exceeds the ceiling

- **WHEN** the worktree copy of a file exceeds the ceiling but its staged blob does not
- **THEN** `pre-commit` admits the commit

#### Scenario: A staged entry holds no source

- **WHEN** a commit stages a symlink or a gitlink whose path has a registered suffix
- **THEN** `pre-commit` measures no object for it

### Requirement: Peer identity markers are keyed, canonical and shared

ETHOS SHALL define one grammar for protected peer identity: the occurrence kinds `url`, `scp`,
`authority` and bare `host`; the marker `<hex32>.<hex32>.private-peer.invalid`, one HMAC-SHA-256 of
a NUL-joined pre-image of version, kind, host, port and path that never hashes scheme or userinfo;
and keyed replacement of project IDs and ports in named closed contexts. Every reader of markers and
every rebuild SHALL use its one left-to-right scan, which a rebuild record extends only as data.

#### Scenario: A URL becomes one marker

- **WHEN** a fed host with a port and a namespace path appears after `//` with userinfo
- **THEN** the host, port and whole leading segments become one marker
- **AND** the scheme, the userinfo and the rest of the line stay byte-identical

#### Scenario: An scp form keeps its colon

- **WHEN** a fed host appears as `git@<H1>:<F1>`
- **THEN** it becomes `git@<marker>:<marker>`, the path a standalone `path` marker
- **AND** the `scp` and `url` markers of the same parts differ

#### Scenario: A key that cannot key refuses

- **WHEN** the key is not 64 lowercase hex characters with at most one trailing newline, or is all
  zero
- **THEN** the reader refuses with `redaction_key_invalid` and nothing is written

#### Scenario: A number in a closed context is replaced

- **WHEN** a fed project ID or port appears in a closed context
- **THEN** it is replaced by a keyed number in its range that differs from the original, every other
  replacement and every fed value and is absent from the domain
- **AND** more than 4,096 probes refuses with `numeric_replacement_exhausted`

#### Scenario: A rebuild record adds data, not grammar

- **WHEN** a rebuild record declares typed spans and merge-request citations, and IDs whose contexts
  it names from the named context set
- **THEN** the shared grammar matches them as data
- **AND** the rebuild matches no occurrence through a grammar of its own, and the record declares no
  context frame

#### Scenario: Every reader uses the one scan

- **WHEN** the redaction verb, the push check, the keyless verifier or a rebuild reads a line
- **THEN** each uses the one left-to-right scan, which takes the longest declared entry of the
  applicable form at each position and never rescans its output
- **AND** each named context pattern matches what it matched before it was named

#### Scenario: A context an adopter needs joins the named set

- **WHEN** an adopter's ID occurs in a context that no named pattern matches
- **THEN** that context joins the named set as data with its own test, so every keyless reader and
  the push check match it

#### Scenario: An occurrence gives one result

- **WHEN** an occurrence matches one declared entry, or declared entries cross inside it
- **THEN** the occurrence gives exactly one result

#### Scenario: An encoded path is replaced

- **WHEN** a path that the record declares occurs percent-encoded
- **THEN** that occurrence is replaced as the declared path

#### Scenario: A merge-request citation is one span

- **WHEN** a commit message cites `<path>!<n>` and the record declares that citation
- **THEN** the citation, its `!<n>` included, is replaced as one span

#### Scenario: Digits inside a digest stay

- **WHEN** a declared ID's digits occur inside a hexadecimal digest, or outside every context that
  the record names for that ID
- **THEN** those digits stay unchanged

### Requirement: Marker edits in record roots reproduce what they replace

Commit validation SHALL judge, without a key, each changed line under an effective record root that
introduces a peer marker: the line SHALL pair one to one with a removed line of the same hunk whose
literal pieces it keeps in order, each marker over one admitted span and each closed-context number
over a digit run that differs only by a number in its range. A marker line without a pair, a
malformed marker and a marker equal to the plain or empty-key digest of its pre-image SHALL refuse.

#### Scenario: A redaction pairs

- **WHEN** a commit replaces the peer identity in a record line with markers and keyed numbers
- **THEN** commit validation admits it

#### Scenario: A marker line has nothing to pair

- **WHEN** a commit adds a marker line in a new file, or changes the words around a marker
- **THEN** commit validation refuses with `record_marker_unpaired`

#### Scenario: A marker is not keyed or not well formed

- **WHEN** a marker equals the plain SHA-256 or the empty-key HMAC of its pre-image, or a run of
  hexadecimal labels ends like a marker but is none
- **THEN** commit validation refuses with `record_marker_unkeyed` or `record_marker_malformed`

#### Scenario: No profile of the range reads

- **WHEN** neither the incumbent baseline's profile nor the proposed head's can be read
- **THEN** commit validation refuses with `record_roots_unread`

#### Scenario: A record describes the marker

- **WHEN** a record names the marker's form by placeholder labels, or names its suffix alone
- **THEN** commit validation admits the line

#### Scenario: A marker over an encoded path or a citation pairs

- **WHEN** a commit replaces a percent-encoded path, or a `<path>!<n>` citation, in a record line
  with a marker
- **THEN** commit validation pairs that marker with the removed line and admits the line

### Requirement: The rules binding declares only the tables its readers consult

`rules.toml` SHALL declare only `[paradigm]`, `[profiles]` and `[[rule]]`, apart from an
`[artifacts]` table that retires into the profile's `record_roots` and a `[quality]` table whose
`code_size` becomes a `[paradigm.size]` value. The paradigm SHALL report every other top-level key
as `rules-binding`, and the repair SHALL delete such a table, or the binding once it declares
nothing, and SHALL leave a bare value reported.

#### Scenario: A rules binding declares a table no reader consults

- **WHEN** `.ethos/rules.toml` declares `[formats]` or `[gates]`
- **THEN** the paradigm reports the table and the repair deletes it
- **AND** a rules binding left with no table is deleted

#### Scenario: A rules table with its own move is kept

- **WHEN** `.ethos/rules.toml` declares `[artifacts]`, or a `[quality]` table that holds
  `code_size`, alone or beside another key
- **THEN** the paradigm reports neither as `rules-binding`, and the repair deletes neither

#### Scenario: A bare value stays reported

- **WHEN** `.ethos/rules.toml` declares a top-level key that is not a table, such as
  `formats = "TOML"`
- **THEN** the paradigm reports it as `rules-binding` and the repair leaves it

### Requirement: The release table declares only the release mirror

The release binding's `[release]` table SHALL declare only `mirror`, the one key its reader
consults, whether or not the binding protects release tags. The paradigm SHALL report every other
key as `release-binding`, and the repair SHALL delete such a key when it sits on a line of its own,
and the table once it declares nothing.

#### Scenario: A release table restates the version source

- **WHEN** `.ethos/release.toml` declares `[release]` with `version_source`, `tag_pattern` and
  `mirror`, and no protected release tags
- **THEN** the paradigm reports `version_source` and `tag_pattern`, and the repair deletes them and
  keeps `mirror`
- **AND** a `[release]` table left with no key is removed with the comments above it

#### Scenario: A multi-line value beside the mirror stays reported

- **WHEN** an unread `[release]` key holds a value that spans several lines beside `mirror`
- **THEN** the paradigm reports the key and the repair leaves it

### Requirement: A verified retained original is not an authored document

An original that the docs registry verifies against the declared retained origins is not an
authored document: the front-matter, decision-record-name, authored-name and formatter rules
SHALL NOT apply to it, and the repair SHALL plan no edit of it. An original whose observation has a
gap, differs from its declaration or is missing SHALL keep every one of those rules.

#### Scenario: A verified original

- **WHEN** the native observer verifies a declared original's bytes and mode
- **THEN** the paradigm reports no front-matter, decision-record, authored-name or formatter gap
  for it, and `ethos lane repair-paradigm` plans no edit of it

#### Scenario: An original that does not verify

- **WHEN** a declared original's bytes or mode changed, the taxonomy is malformed, or the original
  is declared without an observation
- **THEN** the paradigm judges it as an authored document

#### Scenario: An authored document

- **WHEN** a tracked document under the docs root is no declared original and has no front matter
- **THEN** the paradigm reports its front-matter gap

### Requirement: Governed repositories keep a version identity

Every governed repository SHALL keep `VERSION` as its only version source and `CHANGELOG.md` in
Keep a Changelog 1.1.0 with an `[Unreleased]` section and bracketed version headings. A root
`package.json` `version` or `pyproject.toml` `project.version` equal to `VERSION` SHALL count as
its projection. No repair SHALL choose a version; the license grant SHALL stay a duty of released
repositories.

#### Scenario: A second version source exists

- **WHEN** a governed repository keeps a literal version in `package.json` that differs from
  `VERSION`
- **THEN** the paradigm reports two version sources.

#### Scenario: The Python manifest projects VERSION

- **WHEN** a governed repository's `pyproject.toml` declares the `project.version` that `VERSION`
  holds
- **THEN** the paradigm reports no version-source gap
- **AND** a different literal version reports two version sources.

#### Scenario: The npm manifest projects VERSION

- **WHEN** a governed repository's root `package.json` declares the version that `VERSION` holds
- **THEN** the paradigm reports no version-source gap
- **AND** the same manifest without `VERSION` reports the missing source once, naming its version.

#### Scenario: A version heading is unbracketed

- **WHEN** `CHANGELOG.md` contains `## 1.2.0 - 2026-10-14`
- **THEN** the paradigm reports a non-standard version heading.

#### Scenario: An untagged repository has no version

- **WHEN** a governed repository declares no release tags and tracks no `VERSION`
- **THEN** the paradigm reports the missing version source
- **AND** it reports no license gap for a missing `LICENSE`

### Requirement: Released products tag their version

A repository that publishes releases SHALL protect release tags as `v` followed by a Semantic
Versioning version, and each tag SHALL name the `VERSION` that its version identity keeps.

#### Scenario: A release tag pattern differs

- **WHEN** the release binding protects tags other than `v*`
- **THEN** the paradigm reports the release tag pattern

### Requirement: Markdown list items have one blank-line rule

Inside a Markdown list item, a paragraph that follows another block, and a block that follows a
non-paragraph block, SHALL be preceded by one blank line; a block that follows its introducing
paragraph SHALL follow it directly. An item holding such a separator SHALL be followed by one blank
line; any other item SHALL be followed directly by the next. The Markdown fix, check, gate and
`pre-commit` SHALL apply this rule to every authored Markdown file.

#### Scenario: A stray blank line follows a one-paragraph item

- **WHEN** a Markdown list separates its one-paragraph items with blank lines
- **THEN** `check` and the Markdown gate fail with the file and line, `fix` removes the lines, and a
  second `fix` changes nothing.

#### Scenario: A blank line separates a paragraph from the block it introduces

- **WHEN** a list item's paragraph is followed by a blank line and then a nested list or code block
- **THEN** `check` fails, and `fix` joins the block to its paragraph.

#### Scenario: An item holds two paragraphs

- **WHEN** a list item holds two paragraphs and the next item follows it directly
- **THEN** `fix` writes one blank line after the item, and `check` then passes.

#### Scenario: A violation is staged

- **WHEN** a commit stages an authored Markdown file that breaks the list rule
- **THEN** `pre-commit` refuses with the file's path and the line of the first violation.

### Requirement: Text without a native formatter has one canonical layout

Authored text whose format owner is `repository-canonical-text` SHALL have no blank line at its
start or end, at most one blank line in a row and one final newline, with whitespace-only lines
empty; an empty file SHALL stay empty, and content lines SHALL keep their bytes. `lane format`, the
source-format gate and `pre-commit` SHALL apply this layout in every governed repository.

#### Scenario: A hygiene file holds a doubled blank line

- **WHEN** a tracked `.gitignore` separates two patterns with two blank lines
- **THEN** `ethos lane format --check` and the source-format gate fail, and `--apply` leaves one
  blank line.

#### Scenario: A canonical-text file ends without a newline

- **WHEN** `VERSION` holds its version with no final newline
- **THEN** the check fails, and the fix adds the newline.

#### Scenario: A violation is staged

- **WHEN** a commit stages a canonical-text file with a blank line at its start
- **THEN** `pre-commit` refuses with the file's path and the line that differs.

### Requirement: Python packages state their purpose

Every tracked `__init__.py` that a repository authors SHALL open with a docstring that names its
package's purpose; an empty marker or one without a docstring SHALL be a paradigm gap. The paradigm
report SHALL name each one, and `pre-commit` SHALL refuse a staged one.

#### Scenario: A package marker is empty

- **WHEN** a repository tracks an empty `src/app/__init__.py`
- **THEN** the paradigm reports `repository_paradigm_package_docstring:src/app/__init__.py`.

#### Scenario: A package marker states its purpose

- **WHEN** `src/app/__init__.py` opens with `"""Application commands."""`
- **THEN** the paradigm reports no package gap.

#### Scenario: An empty marker is staged

- **WHEN** a commit stages an empty `__init__.py`
- **THEN** `pre-commit` refuses with `pre_commit_package_docstring` and the file's path.
