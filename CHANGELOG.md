# Changelog

All notable ETHOS changes are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and product versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Commit subjects follow Conventional Commits; they do not replace curated release notes.

Historical entries preserve recorded changes and dates; they do not by themselves
prove a tag, published package or hosted release. Release evidence and unresolved
historical bindings are governed by [Release Governance](docs/governance/release-governance.md).

## [Unreleased]

## [0.2.0-alpha.17] - 2026-10-28

### Changed

- The decisions index lists every number from DR-0001 to DR-0016 in order. A deleted record keeps
  one line with its status, its decision date, its successor and a reachable commit that holds its
  last text.
- The product design contract carries the full meaning of 雅 (aesthetic judgment, taste, and
  artistic and cultural refinement, assessed in the rendered whole), and the Docs Registry and the
  terminal plan link to it.
- The terminal plan names the repository paradigm as the owner of per-file limits, and it lets a
  measured iteration cost that every later Change pays be removed ahead of the batches.
- Accepted specs, unshipped documents, research, history, Skills, CONTRIBUTING, README and the
  glossary no longer describe removed behavior or cite deleted files. Pinned commits that a history
  repair rewrote now cite their reachable twins.
- The Work Lane coordination requirements of the repository-governance specification describe the
  current Lease, handoff, refresh, retirement and publication behavior: retirement consumes an exact
  reviewed receipt rather than a preservation package, and handoffs record a package and effect
  Attestation rather than Chronicle.

### Fixed

- Runtime generation reclamation no longer defers when another process deletes a path that a
  running command names while reclamation is observing it. A path deleted after its existence
  check is an observed absence, as if it had been absent from the start; a dangling symbolic link
  still defers reclamation. Concurrent test workers hit this race in a full proof.

## [0.2.0-alpha.16] - 2026-10-27

### Fixed

- A refused commit to a protected branch no longer loses its content. When the
  reference-transaction hook refused, for example, `git commit` on `dev` in the accepted checkout,
  its compensation reset the index and worktree to `dev`, and the edits survived only in an
  unnamed, unreferenced commit. The hook now restores the checkout only when another ref already
  contains the refused commit, as after a refused fast-forward. Otherwise it keeps the staged
  content and names the refused commit.
- Retained adopters can migrate an owned legacy Work Lane name through `ethos lane repair-paradigm`
  without changing its files, index intent, holder or Lease expiry. An interrupted projection
  recovers forward from the attested ref transaction only while the exact current binding remains
  admitted. Worktree binding reads now select only the renamed worktrees and still recheck each
  affected HEAD before writing it.
- Explicit runtime supply is validated against its own manifest and repository scope instead of
  the activation coordinator's lock. Upgrade and rollback keep manifest-bound predecessor
  selection distinct from activation coordination and accepted self-hosted source authority.
- Runtime materialization no longer ignores an interpreter that `uv python list` reports by a
  relative path. It now lists uv's candidates in an explicit working directory and resolves
  relative paths there. Every candidate still passes the same executable, version, ABI,
  architecture, prefix and copyable-image checks.
- On macOS, a command that failed while ETHOS cleaned up its owned processes no longer loses its
  own failure. When a command's leader exited just as cleanup interrupted it, Darwin refused the
  signal to its process group, and cleanup reported `command_scope_cleanup_failed` in place of the
  command's error. Cleanup now leaves such a group to its bounded close, which already waits for
  Darwin to reap exited members. A refusal while the leader still runs still fails cleanup.
- `status` and `prewrite` no longer exceed their execution deadline in a repository whose history
  holds signature repairs. Archive resolution verified the whole repair history for every archive
  commit, including commits that a repair did not affect. It now selects only the repairs in each
  commit's affected history and shares their verification within one observation.
- The commit hook judges both sides of a staged rename. Git's rename detection listed only the
  new path, so moving a file out of a governed path was judged as an addition alone.
- On macOS, lane retirement no longer counts a FIFO that `lsof` reports by inode alone as open
  content inside the worktree. Reviewed retirement content admits only regular files,
  directories and symlinks.

### Security

- The wheels and installed runtimes ship npm 12.2.1 as a production Node module, which runtime
  materialization uses to install the locked Node supply; the development and CI supply use it
  too. npm's bundled undici 6.29.0 (GHSA-4qv8-2p9j-2685, GHSA-xjj6-f33q-929c) and ip-address 10.7.2
  (GHSA-rxp7-6hxx-x8q5) carry known advisories, and no npm release fixes them yet. The dependency
  gate reports them without blocking, as its policy requires for findings with no fixed stable
  release. The npm launcher package does not contain them.

## [0.2.0-alpha.15] - 2026-10-26

### Fixed

- On Windows, repository-declared commands that ETHOS runs in the locked toolchain now find host
  commands such as `git` and `tar`. Their PATH listed the locked tools followed only by Python's
  default search path, which on Windows is `.;C:\bin`: it names no system directory and includes
  the current directory. PATH now ends with the host's command directories. POSIX keeps
  `/bin:/usr/bin`. Windows gets `%SystemRoot%\System32`, `%SystemRoot%` and the directory of Git's
  shell-free launcher; a Git directory that also holds a shell, such as Git for Windows' `bin`,
  never joins.

## [0.2.0-alpha.14] - 2026-10-26

### Changed

- The locked supply moves to the latest stable releases that ETHOS's constraints allow: mise
  2026.10.19, which ETHOS's own repository now requires and its CI bootstraps, Node 26.12.1,
  Python 3.14.9, Go 1.27.3, Syft 1.55.0, Vale 3.25.1, OpenSpec 1.15.0, markdownlint-cli2 0.24.0,
  Allure 3.22.1 and the latest stable releases in the Python lock, among them uv 0.13.5 and ruff
  0.17.2. The supported Python versions remain 3.12 through 3.14. The CI model pins setup-uv
  10.3.2, docker/login-action 4.7.0 and jdx/mise-action 5.2.3 by commit; mise-action 5 delays only
  an unpinned mise release, and the model always names one.

### Removed

- The docs registry, decision records and docs health no longer read metadata wrapped in a
  leading HTML comment; plain front matter is the only carrier. A wrapped document declares no
  metadata, and the repository paradigm reports the wrapper, which
  `ethos lane repair-paradigm --apply` removes. The `docs_title_not_first` gap retires with the
  carrier.

### Fixed

- Locked tools whose installed copy mise selects only for trusted configuration, such as
  aube-locked npm packages, now resolve for repositories that native mise reports as trusted.
  ETHOS resolves in a disposable copy of the declarations, which mise never trusted, so it reported
  those tools missing. Resolution now asks native mise, under the caller's own trust inputs,
  whether the repository is trusted, and carries only that answer to the copy for one invocation,
  in safe mode and with disposable state; it writes no trust record. A refusal for an untrusted
  repository names `mise --cd <root> trust` as the next action. Provisioning a locked tool whose
  archive is not cached carries the same trust, so a source checkout can provision it outside CI.
- On Windows the JavaScript behavior gate now loads Node's test reporter. Node loads reporters as
  module URLs and read the absolute reporter path as the URL scheme `c:`, so every run ended with
  an empty journal. The reporter is now passed as a file URL.
- codespell and Vale now check every selected Markdown file, including one whose name looks like an
  option. Without `--` before the inputs, such a name could be read as an option instead of a file.

## [0.2.0-alpha.13] - 2026-10-25

### Fixed

- Host link checks now include tracked edits and nonignored new authored Markdown instead of
  rejecting changed inputs or silently omitting new ones. A tracked file deleted from the working
  tree without staging the deletion is no longer a candidate member: the other links still pass,
  and a link to that file fails as undelivered. A member that appears or disappears while the check
  runs is refused. Candidate results remain separate from exact committed proof; native input
  ownership, bounded reads and change detection remain enforced.
- Native tool resolution and disposable provisioning keep mise's state in their disposable
  directories. Earlier runtimes left a record in the host's mise state for every resolution, each
  pointing at a deleted temporary configuration; `mise prune --configs` removes those records.
- Repository commands that ETHOS admits can run their own mise tasks again. Their environment no
  longer carries the safe mode that resolution uses, which made `mise run` refuse with "running
  tasks is disabled in safe mode". A caller's explicit `MISE_SAFE` and state directory still apply,
  and trust remains mise's own decision.

## [0.2.0-alpha.12] - 2026-10-24

### Fixed

- `ethos hook install` run by a newer package no longer selects that package manager's
  installation in place when it upgrades a repository or replaces a removed one. Like a first bind,
  it pins the runtime into the sealed host store. A Mise installation stays writable so that
  `mise uninstall` can remove it, and after an upgrade one Python run from it could damage the
  selected runtime, which status then reported as `runtime_payload_mismatch`.
- The published Mise declaration puts only the `ethos` console on `PATH`. Its `bin_path` named the
  runtime's script directory, so `mise exec` and activated shells of an adopter ran ETHOS's own
  `python`, `uv`, `ruff` and other bundled tools ahead of the adopter's, and Python runs from there
  wrote bytecode into the installation. Each runtime archive now carries `ethos/bin`, which holds
  only the console.

## [0.2.0-alpha.11] - 2026-10-24

### Fixed

- A full proof of a repository that declares `[[proof.source_contracts]]` no longer ends with
  `source_contract_invalid` after every gate passed. The proof's transition plan freezes its
  policy, and source-contract decoding rejected the frozen form, which also hid the declared
  artifact classification from the quality floor. The defect was observed on 0.2.0-alpha.7 and was
  still present in 0.2.0-alpha.10.

## [0.2.0-alpha.10] - 2026-10-24

### Changed

- 0.2.0-alpha.9 was tagged but not released: advisories published after its hosted verification
  blocked its release build. This release is the first to publish the changes listed under
  0.2.0-alpha.9 and 0.2.0-alpha.8.

### Security

- The Python lock selects fastmcp and fastmcp-slim 4.1.3, fixing GHSA-7xgj-8392-5q4r and
  GHSA-vqqp-x5qm-5qp4 in 4.1.1, and virtualenv 21.14.13, fixing GHSA-cx6f-vjhg-g3cc in 21.14.11.
  ETHOS requires fastmcp 4.1.3 or later, and fastmcp-slim 4.1.3 adds certifi 2026.10.23 to the
  runtime.

## [0.2.0-alpha.9] - 2026-10-23

### Changed

- 0.2.0-alpha.8 was selected but not published: its source fails every Windows leg of hosted
  conformance on the Taplo false clean fixed below. This release is the first to publish the
  changes listed under 0.2.0-alpha.8.
- Release Governance defines the prerelease stages by evidence on the journeys a release target
  declares: beta needs hosted verification on every supported platform, the adopter journey from the
  published artifacts on macOS and Linux and no known blocking defect; a release candidate and stable
  follow 72 hours and 7 days of adopter use without one. 0.2.0 declares installation through Mise
  from the GitHub release through release on macOS, Linux and Windows. GitLab-hosted CI, GitLab
  publication and the Homebrew channel are not 0.2.0 preconditions.

### Fixed

- The source-format check takes a TOML file as formatted only when Taplo's check run reports
  collecting every file it was given, and renders the file alone otherwise. Taplo exits cleanly when
  it collects no file, so since the check runs were batched a misformatted TOML file that it did not
  collect, such as one whose name holds a backslash, passed unformatted. Every Windows leg of hosted
  conformance failed since then at the installed format journey with
  `installed_source_format_unproven:preview_or_check`.
- `ethos hook retire-supply --apply` measured each planned installation after removing it, so its
  report listed every retired installation with 0 bytes and a retirable total of 0. It now
  measures the plan before removing anything, and the apply reports what the preview showed and
  what it reclaimed.

## [0.2.0-alpha.8] - 2026-10-23

### Added

- `ethos hook retire-supply` previews the host-store installations pinned before consumers were
  recorded: it keeps each one that a repository under the scanned roots selects, holds as rollback
  or cannot read, that a running process uses, or that changed within the grace period, and lists
  the rest with their sizes. `--expect-plan <digest> --apply --authorize` retires exactly the
  previewed plan and records the repositories that still use the installations it keeps.
- Installed CI projection supplies a common CUE verification model and its locked native
  compiler. `ethos lane project` previews, checks and applies one exact admitted patch from
  repository-owned CUE and typed inputs, without an ETHOS checkout or copied `tools.ci`.
  This increment covers source workflows, not offline release acquisition. Local installed
  consumption is qualified; public-archive and hosted adopter execution remain separate
  acceptance boundaries.
- The common verification model composes declared per-runner preparation before locked
  installation, provider-specific native supply checks before proof, and additional evidence
  beside the required report. Runner variables retain full history; platform, trust and
  time bounds remain product-owned. GitLab binds an existing offline-candidate variable and
  retains additive offline jobs without replacing protected request admission; Windows evidence
  preparation uses one native command. Source generation does not replace retained release/offline
  acquisition or establish hosted Windows qualification.
- Repositories can declare runner-provided executables and references in
  `.config/ci/runners.toml`. Ownership applies only to the declared Forge's pipeline files;
  malformed declarations grant no ownership.
- Publication can retire a closed review's unabsorbed proposal when an owned Work Lane or
  that peer's closed-review ref retains its exact tip. Candidate refs cannot retain it;
  without a qualified retainer the proposal remains preserved.

### Changed

- Selecting an installed runtime reuses the payload digests it recorded while each file's exact
  state (device, inode, size, mode, mtime and ctime) is unchanged, instead of hashing every file
  again. A warm selection of the 13,661-file runtime takes 0.17 s instead of 0.67 s; an `ethos`
  command selects its runtime twice and every hook once. Changed bytes or modes and added entries
  are still reported as payload damage, and Windows and small payloads keep hashing every file.
- Proofs compile requirement and scenario names into their Commitment's acceptance identity, so two
  requirements or scenarios with equal bodies stay distinct instead of collapsing into one item.
  Landing hooks and `ethos land` admit a proof carrying either this or the earlier encoding of its
  exact source, so a head proved before the switch still lands, closes out and releases.
- The source-format gate checks the files of each formatter in native check runs, once per
  configuration, instead of rendering every file in its own process; only a file a run reports or
  cannot vouch for is rendered alone, so postimages and diagnostics are unchanged. ETHOS's 1,020
  formatted files take 8.7 s instead of 99.5 s, which also shortens every fixture proof.
- The `bootstrap` task builds the development environment on the Python that
  `.config/mise/config.toml` pins and `mise.lock` locks for every platform, CPython 3.14.8,
  instead of whichever interpreter the host offers first. Python 3.12 remains the compatibility
  floor, and supported versions end at 3.14. A Homebrew patch upgrade had left the
  environment on a framework build that no runtime image can copy, so `hook install` and the
  install smoke failed with `hook_runtime_interpreter_source_unavailable`.
- Reading the Attestation set decodes its members on every read. The set no longer keeps a
  process-wide cache of decoded members, so a repeated read costs what a first read costs;
  a fresh process reads the 2,084-member set in 1.56-1.90 s. Selected membership, custody
  and the file-backed native output capture are unchanged. `cachetools` is no longer declared
  directly; it remains locked as a dependency of `py-key-value-aio`.

### Fixed

- The host runtime store no longer grows by one installation for every activation. A repository
  records itself in each installation it selects or holds as rollback supply, names its preserved
  predecessor in `ethos/runtime/ROLLBACK`, and `hook install` retires each recorded installation that
  no consumer selects or holds and no running process uses. Installations pinned before this release
  have unknown consumers and stay until an explicit, user-approved retirement. Resealing an
  installation no longer rewrites the modes of entries that already hold their seal.
- Generated CI reference admission and repository closure treat a step that the retention
  record keeps, by Forge file, job and text digest, as owned operating-system glue. They had
  read its words as commands: aigw-cli's recorded PowerShell steps yielded 38 unowned
  executables such as `Join-Path` and `Write-Host`, so any patch to its GitLab pipeline was
  refused. A step whose text no longer matches its record is read as commands again.
- Isolated Ruff execution explicitly disables Python bytecode writes. Same-attempt
  evidence with bytecode enabled is refused, and host-store installation pinning and reuse
  reseal runtime directories. Existing damaged installations and failure evidence are
  preserved; these protections do not establish who wrote earlier unexpected files.
- A selected runtime whose readable manifest no longer matches its payload is reported as
  `hook_runtime_payload_mismatch`, and `status` reports `runtime_payload_mismatch`. Bytecode, a
  junction, an unreadable entry or a changed file had been reported as a manifest failure and a
  schema migration, which pointed recovery away from the damaged installation. A missing,
  malformed or mismatched manifest still reports `hook_runtime_manifest_invalid`.
- ETHOS's own dependency audit policy can change through a landing. The landing hook required a
  captured audit to match the policy its own build ships, and for ETHOS's source that is the very
  file being changed, so no renewal, cleanup or new disposition could ever land. For the product's
  own source, a captured audit now binds the policy committed at the exact head, and its raw
  findings are still re-evaluated. Every other repository still refuses a proof captured under a
  different product policy.
- Generated CI reference admission reads GitLab `before_script` and `after_script`, which it
  skipped, including nested script arrays and native array anchors, so an unowned command
  there is refused like one in `script`. A GitHub `${{ … }}`
  expression inside a `run` step is a value, so text after it is never taken as a command name.
- Historical signature-repair records are validated against the release-mirror location their
  source commit declared. Moving the mirror to `.ethos/release.toml` on 2026-10-16 made every
  record whose source declared it in the workspace binding fail
  `signature_repair_source_coordinates_mismatch`, so proposal and absorbed-lane retirement
  raised instead of observing conservation (DR-0013).
- Attestation set updates keep ending members after a ref is deleted. A retirement's deletion
  publication was counted as a selected tip, and its zero object made lifetime reachability
  unobservable, so every later update kept every member and reported
  `attestation_lifetime_reachability_unavailable`. A deletion is now its ref's latest
  publication but selects no commit.
- Authored-text validation runs before formatter selection, covering declared plain-text,
  INI, vocabulary and extensionless carriers as well as formatter inputs. Invalid UTF-8,
  NUL bytes and missing inputs are refused without writes; generated, upstream, archived
  and binary inputs keep their declared boundaries.
- The MIT license floor requires an actual named copyright holder even when a repository
  has no package metadata. A placeholder or empty holder does not establish a valid grant.

### Security

- The npm lock selects npm 12.2.1 and overrides Allure's `dompurify` 3.4.16 with 3.4.17,
  fixing the advisories in those replaced versions. Superseded audit dispositions are
  removed; findings without an official stable fix remain explicitly reported, and
  fixable findings still block. This retires the superseded npm dispositions and reports
  the unfixed braces advisory without accepting risk. The product lock remains the sole
  npm package owner.

## [0.2.0-alpha.7] - 2026-10-22

### Changed

- ETHOS is released under the MIT License instead of the Apache License 2.0. The MIT grant
  applies from 0.2.0-alpha.7; earlier releases keep the Apache-2.0 grant they shipped with.

### Fixed

- The hosted release can build its Windows runtime. The Windows leg of the 0.2.0-alpha.6 release
  stopped at `git_object_trust_anchor_unprotected` while binding the operator's commit trust, so
  that pre-release has no Windows archive: the CI binder restricted the signer file with POSIX
  modes, which leave a Windows ACL unchanged, and the hosted temporary root lets other users
  write. The binder now protects the file and its directory through the host's own protection
  authority, which the trust check observes, and keeps the signer file's LF line endings.
- Formatting, Markdown lint and prose share one judgement of authored text. A file whose content
  Git classifies as binary, such as Markdown that holds a NUL byte, is reported as
  `authored_text_binary:<path>` before any native tool reads it, and `lane format --apply` refuses
  it without writing; such a file used to pass, because the formatters keep its bytes. Git's
  classification of the worktree bytes decides, not a list of characters. The `text` and `eol`
  attributes only govern line-ending conversion, so a valid document marked `-text` passes.
- A command timeout's cleanup no longer fails on macOS when the timed-out process group's members
  have exited but are not yet reaped. `ethos publish` showed a `PermissionError` traceback instead
  of its unavailable remote observation. A member that stays unsignalable past the cleanup bound
  still fails the command.
- An exact `--patch` to a generated CI file admits the references its repository already owns.
  Release peers own their forge provider and Git remote, `mise exec … --` owns the command it
  runs, a governed repository may run the product's own runtime executables, such as `git`, and
  `requires-python` owns the interpreter. A one-line edit to an adopter's GitLab pipeline was
  refused with `product_reference_not_admitted_at_baseline:executable:git`. An executable that no
  declaration owns stays refused in `run` and `script` steps; commands in GitLab `before_script`
  and `after_script` are not yet observed.

## [0.2.0-alpha.6] - 2026-10-22

### Added

- An upstream source contract may name a committed received archive as
  `<path>.zip#sha256:<hex>`, for supplies released as a ZIP rather than an npm package. The
  source-integrity gate checks the archive's pinned SHA-256 and compares each declared member with
  its exact entry in memory, without extracting it; unselected entries stay unread, and a
  missing, unqualified or different entry leaves its members unproven.
- The repository paradigm judges each tracked file's line endings by its effective Git `text` and
  `eol` attributes, which `git check-attr` resolves from every applicable pattern. It checked only
  the last catch-all `*` pattern, so a later or nested pattern could still check a file out with
  CRLF or a host-dependent line ending. Such a file is now a `line-ending` gap; a file marked
  `-text` keeps its exact bytes, and a checkout that Git does not report blocks.
- The repository paradigm judges a tracked license grant. A root `LICENSE` must keep the standard
  text of one license whose SPDX template ETHOS pins by digest (MIT and Apache-2.0, from SPDX
  license-list-data v3.29.0), matched as the SPDX matching guidelines describe, with any
  copyright notice the template requires naming its holder and only the template's own title
  before it. A license outside that list is the repository's own text, which its package
  metadata names by a `LicenseRef-` identifier. `README.md` must link the grant, and every
  root `package.json`, `package-lock.json` or `pyproject.toml` that declares a license must name
  the same identifier. The license is the repository's choice, and a repository without a
  package needs none. The ETHOS README now links its license.

### Removed

- The shipped format-selection policy no longer names the retired
  `integrations/architecture-publisher` capture paths, removed from this repository on
  2026-10-14. Read-only checks no longer consult shipped byte-bound ownership; archived records
  stay excluded by path, and a repository's own carriers still bind only its formatters.

### Fixed

- The hosted release dispatch builds the release wheel on each platform it qualifies. The ETHOS
  wheel carries its platform's Node and Vale, so the one Linux x64 wheel that the 0.2.0-alpha.5
  dispatch built cannot install on Linux arm64, macOS or Windows; that version keeps its signed
  source tag and has no hosted pre-release. Publication also reads a Windows runner's archive
  path, so a qualified Windows leg is published instead of stopping the release.
- An installed console launcher that finds no single entry point for its name now says so on
  stderr before exiting 127; it exited silently. On Windows, shared-supply qualification failed
  at `mise exec -- ethos --version` with no output, so a failed Mise step now reports its exit
  status and output, and the installation takes the product version as its label, as adopters
  declare it, which shortens the path `cmd` must run from about 297 to 214 characters.
- A runtime an earlier ETHOS installed stays preservable. Hook installation pinned the previous
  runtime for rollback, and accepted a selected runtime pinned outside the repository, only if
  its `bin/ethos` equalled the current launcher, so any launcher change blocked every upgrade
  from an older runtime. The manifest still binds every runtime file; only reusing a runtime as
  the current build requires the current launcher.
- A runtime that Mise installs on Windows keeps its identity. Mise extracts archives without their
  file modes on Windows, so the installed files lack the read-only attribute of the sealed
  runtime, and the manifest check refused the installation that had just run `ethos --version`.
  On Windows the runtime identity now binds each file's content and its permissions without the
  write bits, which is what a sealed runtime records, so existing runtime digests are unchanged;
  POSIX modes stay bound in full. Installed-command acceptance also allows each command 600
  seconds instead of 180, because a hosted Windows runner timed out while installing a hook.
- An adopter's `ethos prove --gate` selection of a packaged gate that has no provider, such as
  `ruff` or `dependency-vulnerabilities`, returns `proof_gate_not_importable:<id>`, also when
  another selected gate depends on it. Such a gate runs the product's own Nox session, which
  an adopter does not have. Provider-backed packaged gates, such as the shared floors and
  `external-links`, still run in process.

## [0.2.0-alpha.5] - 2026-10-21

### Added

- A dispatch of the ETHOS CI workflow from accepted `main` with `release_tag` and `release_head`
  builds the release wheel once, qualifies it on Linux x64 and arm64, macOS arm64 and Windows x64,
  and publishes a GitHub pre-release whose archives match their qualification evidence, with
  `SHA256SUMS` and a Mise `http:ethos` declaration. A hosted runner holds no repository proof, so
  `nox -s build` and `nox -s install_smoke` accept `--tag v<version>` beside `--expect-head` and
  admit only the trusted signed tag of that exact source, version and curated entry; an unsigned,
  untrusted, misplaced or mismatched tag is refused before any build effect.
- A repository may declare its own byte-bound carriers in
  `.config/checks/format-selection/policy.toml`. Each `[[ownership]]` record names explicit
  `paths`, `format_owner = "immutable-carrier"`, `mutation_policy = "forbidden"` and a
  `validation_owner` from the repository's full proof set, whose gate verifies those bytes. Every
  formatter and every format check skips a bound file, while Markdown lint, prose, link and
  configuration validation still read it: forbidding a rewrite exempts no file from validation.
  Any other table or field, a gate outside the full proof set, or a linked or unreadable increment
  is refused as `format_selection_increment_invalid`, and a path the product already owns reports
  `multiple primary quality owners`.

### Changed

- A CI step may keep a shell program only as an official installer or operating-system glue that
  `.config/ci/retained-steps.toml` records by Forge file, job and the SHA-256 of the step text,
  with its owner, reason, platforms and target-platform evidence. Every listed job must still
  carry that exact text, so an edited step reports inline shell again and its record as stale.
  Gates and steps that run tracked scripts gain no such record.
- Accepted closeout renames a legacy release branch such as `master` to `main` with its worktree,
  in the same ref transaction as any legacy accepted and candidate names and from the accepted
  root under whichever name its table gives it, instead of refusing with
  `legacy_release_rename_unsupported`. Publication retirement deletes a published legacy release
  ref and refs under a legacy proposal prefix such as `submit/` only when the workspace table
  committed at the ref's head names them; an unreadable table grants no deletion. A peer that still
  serves the legacy release name as its default branch refuses the deletion, so move each peer's
  default branch to `main` first.
- **Breaking:** declared native outputs use tool-neutral formats: `junit-xml`, `cobertura-xml`
  (renamed from `coverage-xml`), `lcov` and `sarif`; `ruff-json` is removed. A Nox report, pytest
  events and a Python runtime report are optional and checked only when declared. `code_quality`
  judges native reports for every language by property and claims only the files they cover, so a
  repository's own tests and analyzers can evidence languages ETHOS does not check itself.
- A full proof waits for its repository's proof slot and until the host's 1- and 5-minute load
  averages are within `ETHOS_PROOF_HOST_LOAD_LIMIT` before any gate runs, so it does not start
  into concurrent proofs or local CI. A Work Lane proof whose candidate moved on ends at admission
  with `candidate_base_stale` instead of running gates for a head that could not land.
- Within one command, ETHOS reads each Git object named by its full ID once and observes the
  running build once; refs, the index, the worktree and failed reads stay fresh.
- Advanced the next product identity to `0.2.0-alpha.5`; local `commit-msg`,
  pre-push, GitHub, and GitLab now consume one repository commit-policy owner
  over the exact introduced commit range.
- Exposed the exact bundled OpenSpec version through the public version surface.
- Upgraded the repository-locked OpenSpec supply to 1.14.0, preserving official
  task source locations and stricter Change-metadata diagnostics. Exact runtime
  and release adoption remain separately verified.
- Converged current Python and npm dependencies, CI images, GitHub Actions,
  downloaded release tools, and the hosted Node LTS/current compatibility
  matrix on verified stable releases.
- Shortened the content-addressed host installation path while retaining
  full-digest ownership, so native Windows runtime modules can load reliably.
- Composed one declared Node test attempt with official c8 coverage reporting,
  retaining preload, concurrency, coverage configuration, failures and warnings.
  Invalid raw evidence is rejected; custody excludes symbolic-link targets.
- Moved locked native tool preparation from CI into the product supply owner.
  Packages include the locked Vale executable, publisher license and common
  prose policy; source and installed consumers use those owned bytes without
  falling back to an ambient executable.
- Active OpenSpec proposals and designs now keep the literal headings of the
  templates that the official CLI resolves, and active Change artifacts share
  the 512-line Markdown ceiling. Proof first archives the selected Change in a
  disposable projection and validates the archived specifications strictly, so
  an over-long MODIFIED requirement fails before any gate runs.
- ETHOS's own gate registry is recognized by Git history shared with the running
  build instead of byte equality with the installed packaged copy, so a product
  registry edit lands ordinarily. Any other repository, including a verbatim
  copy of the product registry, keeps the shared quality floor.
- Repository-authored names may carry a BCP 47 language tag in its canonical case
  as a dot-separated segment, such as `captions.zh-CN.vtt`. Paths that Git
  attributes mark `linguist-vendored` or `linguist-generated` keep their upstream
  names.
- Lane retirement's open-file observation covers the processes the invoking user
  may inspect. On Linux, a process that denies every `/proc` entry `lsof` reads,
  its descriptor links and threads' entries included, is uninspectable rather than
  an incomplete observation, so non-root users can retire reviewed content; each
  admission reports such processes once by PID, UID and command, a recovered
  retirement reports the admission that removed the worktree, and Darwin, whose
  `lsof` omits them, reports the list as unavailable.

### Removed

- Retired the experimental Node coverage collector and unused LCOV interpretation.
- Retired the `python-size` gate; the repository paradigm report measures the
  same 512 effective-line ceiling in the repository audit.

### Fixed

- A new OpenSpec Change bootstraps beside legacy Changes that keep dated names. The official list
  read refused every listed name that broke the logical naming rule; it now refuses only a
  malformed or repeated name, and the new target still meets the rule.
- A package manager can remove the runtime archive it installed. Archive directories open to
  their owner while file modes and bytes stay in the runtime digest, so `mise uninstall` no longer
  fails with Permission denied on a sealed tree. Shared-supply qualification installs the archive
  as a locked Mise `http:` tool, runs its relocated `ethos` console and uninstalls it natively.
- Windows runtimes write relocatable `Scripts/<name>.cmd` console launchers. The rewrite looked
  for console scripts beside the interpreter, where Windows keeps none, and kept the installer's
  launcher, which names the build-time interpreter.
- The configuration quality gate no longer fetches the schema a TOML document declares. Taplo
  still loaded a `$schema` key or a `#:schema` directive under `--no-schema`, so the gate failed
  offline and depended on remote content, such as a knip schema on unpkg. The shipped Taplo
  configuration now disables schemas, and the gate lints with it alone, because a repository
  increment adds nothing to a schema-free lint.
- Patch admission and `lane format --apply` give `git apply` the patch as bytes. A Windows text
  stream writes each newline as CRLF, and Git read each carriage return as trailing whitespace, so
  on Windows patch admission refused every installed format apply as a preimage mismatch.
- Quality script discovery reports `quality_script_discovery_unknown` when `git grep` writes an
  error, such as an unreadable blob, even though another script matched and Git exited 0. The
  unreadable file was dropped from script roles without a gap.
- Accepted closeout of a self-hosted root now names `mise --cd <root> run bootstrap` as its next
  action when the advance leaves the hook runtime, built from the replaced accepted head, stale.
  It named `ethos publish`, while write admission reported `runtime_build_stale` until the lander
  refreshed the environment and reinstalled the hook by hand.
- The prose, Markdown lint, link, source format and configuration quality gates now bind the
  native configuration their tools read, as each gate's `tools` in the gate registry declares,
  Vale's styles and vocabularies included. Changing only one of those files changes the gate's
  bound sources, so a proof made before the change no longer satisfies it. Before, the prose
  gate's Vale configuration was outside its sources and an edited rule could reuse a stale
  result.
- On Windows the link gates decode Lychee's report as the UTF-8 it always writes. Decoding it with
  the ANSI code page failed on the summary's emoji and left both gates unknown.
- The product npm lock overrides markdownlint-cli2's exact `markdown-it` 15.0.1 pin with 15.0.3,
  which fixes GHSA-r7fv-28h4-cvq7; the dependency audit blocked every proof on that finding.
- The locked uv, its CI setup and the Linux supply image base move to uv 0.13.4. Earlier uv
  releases trust a compromised emSign root in their bundled CA store (GHSA-hq85-5cpj-mr62), and
  the dependency audit blocked every proof on that finding.
- Lane retirement on macOS admits the `lsof` record of a revoked descriptor, such as the terminal
  of an ended session, which names `(revoked)` without a type, device or inode and holds no file.
  Any process holding one made the open-file observation unavailable and blocked retirement.
- The repair for an authored-name gap now also names marking the path `linguist-vendored` or
  `linguist-generated` in `.gitattributes`. It named only the kebab-case rename, so adopters were
  told to rename third-party fonts, license and notice files that keep their upstream names once
  marked received.
- The source format, Markdown lint and configuration quality gates read the repository's
  Prettier ignore file at its paradigm carrier, `.config/checks/prettier/prettierignore`, whose
  patterns resolve from that directory. They read only a root `.prettierignore`, so an ignore
  file in its carrier excluded nothing and the immutable records it names reported format drift.
  A root `.prettierignore` is now refused as
  `native_tool_configuration_location_invalid:prettier-ignore`, like any misplaced native
  configuration, and the repository paradigm already reports its move.
- An active proposal or design that lacks a heading of its official template no longer locks
  its repository. Strict validation accepts such a Change, so prewrite previously blocked every
  path on the template gap, including the drifted file and an exact restoring patch. When template
  drift is the only blocking gap, prewrite now admits the selected Change's drifted files, and no
  other path, for repair; any other blocking gap keeps the repair closed.
- Lane retirement no longer counts an empty directory that another process holds open, such as
  an agent's `.claude/.cc-writes`, as content in use; held files and non-empty directories
  still block.
- Limited accepted-source delivery reuse to the current accepted commit;
  other exact push objects retain independent proof and contribution-range
  checks without requiring local accepted-ref equality.
- Validated declared Vale vocabulary with the locked native parser; unconsumed,
  malformed or missing selected vocabulary now fails configuration quality
  without rewriting its source or relying on an ambient executable. Section-only
  vocabulary is compiled while native optional files remain optional.
- Aligned bootstrap and hosted-proof test fixtures with the declared native Vale
  supply, preserving preparation-failure refusal and platform prerequisite checks.
- Refreshed the architecture learning source binding after reviewed continuation
  and retention changes, without changing the authored graph meaning.
- Preserved official OpenSpec apply refusal while admitting repair of its exact
  selected existing task artifact from native schema and tracking observations.
- Allowed planning without an unselected, observably absent local Skill portfolio;
  required, incomplete, dangling and unreadable portfolio state remains blocking.
- Observed the npm dependency audit again, at most three attempts, when npm
  reports that its bulk advisory request itself failed; npm never retries that
  POST. Every attempt stays in the receipt, and findings, malformed reports and
  other native failures are still observed once.
- Stopped Markdown lint from rejecting what Prettier writes: Prettier uses
  underscore emphasis but asterisks inside a word, so an emphasis style is now
  required only in official OpenSpec artifacts, which Prettier does not format.
- Named a Work Lane's worktree family after the canonical checkout that owns the
  Git common directory, so a lane started from an accepted sibling worktree such
  as `<repository>-accepted` lands in `<repository>-worktrees/`.
- Stopped Linux lane retirement from treating a process that exits during the
  open-file scan as an unreadable observation. `lsof` records such a process or
  descriptor only by the `/proc` entry it failed to read, or by the target it read
  before the descriptor's `stat` failed, without a type, device or inode. A scan
  left incomplete by an unreadable record is taken again, at most three times
  within one 30-second timeout, and a record that stays unreadable still blocks
  retirement.
- Stopped Linux lane retirement from treating a netlink socket as an unreadable
  observation. `lsof` prints a socket it finds in the kernel's socket tables by
  its socket inode alone, netlink as unix, and no such socket is a file a
  worktree holds.

## [0.2.0-alpha.2] - 2026-08-30

### Changed

- Repository acceptance, development package builds, and explicit releases now
  have separate identities; accepted source produces a unique PEP 440
  development build instead of silently claiming the release version.
- `proposal/*` is a governed remote review-ref projection; `work/*` remains the
  sole local authoring lane.

### Removed

- Removed the duplicate local `proposal_lane` role and its protected-write
  semantics.
- Removed `channel` and `acceptance_state` from build and runtime manifests.

## [0.2.0-alpha.1] - 2026-08-27

### Added

- The terminal repository trust kernel: canonical Commitment and Attestation
  contracts, deterministic plans, exact Git effects, and post-effect evidence.
- Governed Work Lane and Lease lifecycle, candidate/accepted-root promotion,
  exact object publication, and package-only immutable hook runtimes.
- Repository-native quality, source-budget, evidence, supply-chain, and
  OpenSpec lifecycle gates.

### Changed

- Consolidated the Python implementation into one `ethos` package and removed
  retired compatibility control planes and duplicate lifecycle owners.
- Moved shared mutable runtime state under the Git common directory and made
  generated hooks thin projections over the selected immutable runtime.
- Converged status, plan, proof, mutation, archive, and closeout results on the
  schema-version-2 verdict model.

### Fixed

- Hardened exact-CAS mutation, compensation, ownerless-lane preservation,
  runtime bootstrap, cross-worktree state, and hosted proof execution.

## [0.1.0-alpha.2] - 2026-07-24

### Added

- Release governance files for GitLab visibility: `LICENSE`, `CONTRIBUTING.md`,
  `CHANGELOG.md`, GitLab CI, and GitLab templates.
- Schema validation, gate registry, commit/signature policy, adoption profiles,
  self-evolution ledger, and MCP server descriptor.
- Machine-readable SSH commit signature enforcement for release HEAD checks.
- Secret-scanning gate (gitleaks) and Markdown lint gate (markdownlint-cli2),
  wired into hosted and local CI.

### Changed

- Coverage floor raised to 100% and enforced across
  `coverage.ini`, the test runner, and the coverage policy.
- npm CI jobs install Node from nodejs.org on the cached `python:3.12` image
  instead of pulling the unreachable `node:24` registry image.

### Fixed

- Every CI job auto-retries on infrastructure failures (image-pull timeouts,
  runner faults) while genuine gate breaches still fail immediately.
- Cross-platform coverage: `git_common_dir` and lease-expiry branches are pinned
  so the 100% floor holds on Linux and macOS alike.
- Hardened `coverage.xml` parsing against XXE (defusedxml) and installed Taplo
  from a prebuilt binary to avoid a broken aarch64 source build.
- GitLab verification reclones complete history so replay checks resolve pinned
  commits even when a runner workspace was previously shallow.

## [0.1.0-alpha.1] - 2026-06-30

### Added

- Standalone ETHOS product workspace with six package topology.
- Kernel model, action graph, command plane, evidence/provenance, docs registry,
  claims, local state, assistant projections, and product hardening evidence.
