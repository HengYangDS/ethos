# Changelog

All notable ETHOS changes are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and product versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Commit subjects follow Conventional Commits; they do not replace curated release notes.

Historical entries preserve recorded changes and dates; they do not by themselves
prove a tag, published package or hosted release. Release evidence and unresolved
historical bindings are governed by [Release Governance](docs/governance/release-governance.md).

## [Unreleased]

## [0.2.0-alpha.7] - 2026-10-22

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
