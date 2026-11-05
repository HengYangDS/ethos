# Changelog

All notable ETHOS changes are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and product versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Commit subjects follow Conventional Commits; they do not replace curated release notes.

Historical entries preserve recorded changes and dates; they do not by themselves
prove a tag, published package or hosted release. Release evidence and unresolved
historical bindings are governed by the [distribution specification](openspec/specs/distribution/spec.md).

## [Unreleased]

### Added

- Each release publishes two inventories beside every runtime archive: an SPDX 2.3 SBOM, for
  consumers, and a Syft JSON inventory that captures Go symbols, for binary scans. Both name the
  archive's published file and SHA-256, are covered by `SHA256SUMS` and the build provenance
  attestation, and must hold every component that the runtime's owners declare: the bundled Go
  tools, uv's crates, Node and each shipped Python distribution. An inventory that names another
  archive, or a second declaration, stops the release. So does a required platform without both
  inventories. An optional Windows platform without both is left out, and the release notes name
  it.
- A release run reports the binary-level advisories of the inventories it published, in a
  read-only `release-binary-scan` job that never blocks the release. Its report names Grype and
  its database, each archive's digest, one row per archive, package, version and advisory, the
  executables that no package identifies, and any platform it could not scan. A `scan_tag`
  dispatch scans an already published release again from its inventories. On alpha.29's macOS
  archive the symbol-capturing inventory yields the same 63 advisories as a direct scan of the
  runtime, where an SPDX input yields 113.
- `ethos land --retag <tag>` re-creates a signed release tag whose target a completed signature or
  history repair replaced, on the mapped replacement commit, with the original name, tagger, date
  and message; only the target and the signature change. The preview names each refused tag with
  its gaps and reports one plan digest, and `--apply --authorize --expect-plan-digest <digest>`
  moves the tag refs and records one `release:mapped-retag` attestation per tag. A pruned original
  is restored from the repair's backup bundle. Publication qualifies the re-created tag by the
  proof that its original release record embeds.
- A Work Lane's holder reads and renews its Lease through native commands. `ethos status` names
  `lease_generation`, `lease_expires_at` and `lease_seconds_left` in its summary, which stays inline
  when the detail moves to an artifact, and points at the renewal with less than two hours left, or
  at resumption once the Lease has expired. `ethos lane lease renew` and `resume` without
  coordinates preview from the current Lease and return the exact apply command; an apply without
  all four coordinates refuses with `lease_coordinates_required`.

### Changed

- A result for a gate that the plan does not declare is `gate_undeclared:<gate>`, so
  `gate_unknown:<gate>` means only a gate whose verdict is unknown.
- The Python lock moves to the newest releases that have been public for at least 24 hours:
  coverage 7.17.1, dnspython 2.9.2, filelock 4.2.8, joserfc 1.8.0, platformdirs 4.14.4,
  python-discovery 1.9.4, uncalled-for 0.4.2 and virtualenv 21.15.5. filelock 4.2.9 and
  platformdirs 4.14.5 were younger than that and wait for the next move.
- The kernel schema identifiers move to `https://ethos.invalid/schemas/<name>`, a name reserved
  never to resolve.
- The `release-sbom` gate catalogs the runtime archive that the install smoke keeps, instead of
  the wheel, and now follows `local-install-smoke`. The wheel-only SBOM, which listed one package
  and no purls, is gone.

### Fixed

- `ethos prove --json` keeps each failed gate's own cause after its class code (GitLab issue #2).
  A gate that times out reports `gate_unknown:<gate>` and then `gate_timeout:<gate>`, and the
  proof's verdict stays `unknown` instead of `block`. The result carries one bounded diagnostic per
  failed gate, with its kind, timeout, elapsed time and the count of codes beyond five that it
  omits, and its next action names the timeout to raise. Before, the cause appeared only in the gate
  events and the proof artifact.
- A gate whose prerequisite is unknown, or whose command is absent, is `unknown`; a failed
  prerequisite still blocks it.
- A refusal reports every gap it found, not only the first, and keeps the verdict class that its
  producer declared: a Git timeout and an unknown Git compare-and-swap outcome are `unknown`.
  Status keeps an unknown OpenSpec resolution `unknown`, and a retirement failure keeps its gap's
  subject and the partial-retirement gap.
- The integrity gate reports a generated artifact or received archive whose bytes differ from its
  native owner or pinned original as `block`, with `source_generated_bytes_mismatch:<path>`,
  `source_upstream_member_mismatch:<path>` or `source_upstream_archive_digest_mismatch:<path>`. A
  member it cannot read or compare stays `unknown` with `source_integrity_unproven:<path>`.
- A locked supply refusal blames jdx/mise#15363 only under mise 2026.11.0 and 2026.11.1, and points
  to mise 2026.11.2 or later, which fixes it. Under 2026.11.2 it names trust or installation, as it
  does for an earlier mise.
- A gate child's mise no longer reads the operator's own configuration. The locked execution
  environment stopped mise's configuration walk only at a temporary directory, so a `mise` run from
  the repository went up to the home directory and loaded `~/.config/mise/config.toml` and its
  `conf.d` files as an ancestor's. archpub's npm test took the operator's npm 12.2.2 that way. The
  walk now also stops at the repository's parent, as resolution already did.
- The release journey upgrades from the latest earlier release that GitHub published, not merely
  from the next changelog entry. 0.2.0-beta.1 was tagged but never published, so beta.2's journey
  failed to download it. The receipt names each skipped version as `skipped_unpublished`, and a
  forge error other than a missing release refuses instead of skipping.
- A beta's journey now has to cover every release that governed adopters still upgrade from.
  beta.2 was qualified only on the upgrade from alpha.30, while 8 of 12 governed repositories
  were still on alpha.29. The `journey_previous` dispatch input names earlier published prereleases,
  comma-separated. The journey upgrades from each one, and rolls back to it, in its own host
  store. The receipt lists every predecessor in `previous`, and keys `upgrade_and_rollback` by
  predecessor tag. A name that is not an earlier published release refuses before any download.
- A release tag that an earlier ETHOS released publishes on the proof its own release effect
  bound, verified as recorded from the copy that effect embeds: its identity, schema, subject,
  tree, artifact custody and recorded policy digest. Before, every publication re-judged it
  against the policy the running runtime compiled for the old source, so after a policy change
  every historical tag refused with `proof_attestation_repository_policy_mismatch`, also when
  every peer already held it. A missing, altered or inconsistent bound proof refuses by name, and
  branches keep the current policy. A request that changes no peer now reports
  `remote_push: already_applied`. DR-0018 records the rule.

### Security

- Commit and tag admission refuse a message that names a private-class network address: an
  RFC 1918 or RFC 4193 literal, a loopback or link-local literal, or a host under `.local`,
  `.internal`, `.lan` or `.home.arpa`. The `commit-msg` hook reads the whole message above Git's
  scissors line, and publication judges every commit and tag that it introduces. The gap names
  the class and the revision, never the address. Documentation addresses, reserved example names
  and `localhost` pass.
- ETHOS's own secret scan refuses the same addresses in tracked and staged content. It never reads
  history, and adopters' Gitleaks configurations are unchanged.

## [0.2.0-beta.2] - 2026-11-05

### Added

- `ethos host run [--wait <seconds>] -- <command...>` runs one heavy local command once the
  host-wide queue admits it, and exits with the command's own status.
  - The queue is one per host. It admits runs in arrival order, up to the slots that `host.toml`
    in ETHOS's host root declares, and a holder that exits frees its place without cleanup.
  - A full proof takes the same host slot after its repository's proof slot, so the proofs of two
    repositories no longer overlap.
  - The child receives `ETHOS_HOST_ADMISSION`, so work that it starts joins the admission instead
    of queueing again. It also receives a worker cap in `ETHOS_HOST_CPU_CAP` and
    `PYTEST_XDIST_AUTO_NUM_WORKERS`: the CPUs that `reserved_cpus` leaves, at least one.
  - A wait that reaches its bound names the holder's repository, executable and start time.
  - Only work that runs through ETHOS joins the queue. Renders, model runs and other test runners
    join it by wrapping their command in `ethos host run`.
- `host.toml` declares the host's `slots` (default 1), `reserved_cpus` (default 0) and
  `load_limit`. An out-of-range value is refused with a named gap and never clamped.

### Changed

- 0.2.0-beta.2 is the first published beta. It upgrades directly from 0.2.0-alpha.30, because
  0.2.0-beta.1 was tagged but never published.
- A full proof's load admission waits for two consecutive 1-minute load samples within the limit,
  instead of one, so a short dip between busy phases no longer admits it. The limit comes from
  `ETHOS_PROOF_HOST_LOAD_LIMIT`, then `host.toml`'s `load_limit`, then half the CPUs. A wait that
  reaches its bound names the load, the limit and where the limit came from.
- Not qualified by this beta:
  - the adopter journey on Windows, which no hosted job runs yet;
  - a repository's exit from ETHOS's hook runtime, which has no native command yet;
  - GitLab-hosted CI, GitLab publication and the Homebrew channel, which are not 0.2.0
    preconditions.
- Known open defects, none in a blocking class:
  - `ethos prove --json` reduces a gate's own cause, such as `gate_timeout:<gate>`, to
    `gate_unknown:<gate>` or `gate_failed:<gate>`, and reports a proof whose gate timed out as
    `block`. The gate events and the proof artifact keep the cause.
  - jdx/mise#15363 upstream, which ETHOS refuses with its cause.

### Fixed

- `ethos lane retire absorbed-ref` previews the deletion with the same predicates that the
  reference-transaction hook applies. A ref that the hook would refuse now blocks the preview with
  the hook's own gap, instead of an apply that the hook then refuses.
- A legacy role ref whose standard successor already holds its exact commit can be retired on its
  own, without renaming any other legacy role.
- The Skill portfolio report names each package directory under the Skills root that no active
  record or retirement routes, as `skill_package_unregistered:<directory>`.
- The generated Windows verification jobs retry their source checkout up to three times. A Windows
  runner can briefly hold the executables of the previous job, which made `git clean` fail on
  back-to-back jobs. Adopters receive the retry when they regenerate their CI projections.

### Security

- The locked npm moves to 12.2.2, which bundles undici 6.29.1 and ip-address 10.7.5. That removes
  six of the eight advisories that the `0.2.0-alpha.22` entry lists from the wheels and installed
  runtimes:
  - undici: GHSA-2m5v-pch6-74hx, GHSA-4qv8-2p9j-2685, GHSA-9fm3-97px-rjf6, GHSA-qrxm-fqhp-jwvm
    and GHSA-xjj6-f33q-929c;
  - ip-address: GHSA-rxp7-6hxx-x8q5.

  The owner took npm 12.2.2 before its 24-hour release age, as an exception to the supply rule,
  because it fixes known vulnerabilities in what ETHOS ships.

- Two advisories remain, because npm 12.2.2 still bundles glob 13.0.6 (GHSA-3g3m-2fjr-6pw4) and
  minimatch 10.2.5 (GHSA-g3hv-75wg-m249). No npm release fixes them, so the release build's audit
  reports them as unfixed upstream. It reports no other advisory.

## [0.2.0-beta.1] - 2026-11-04

### Changed

- Note, 2026-11-05: 0.2.0-beta.1 was tagged (`v0.2.0-beta.1`) but never published. The first
  release run had no macOS runtime, because GitHub cancelled that build without a runner. The
  rerun's dependency audit then refused npm 12.2.1, once npm 12.2.2 fixed six of its advisories.
  The owner chose not to ship it; 0.2.0-beta.2 supersedes it.
- 0.2.0-beta.1 promotes the code of 0.2.0-alpha.30 without product changes.
  - Its tag waited for alpha.30's release run, which proves the adopter journey from the published
    artifacts on macOS and Linux: a cold install, host-store pinning, hook binding, a full proof
    and status, an upgrade from 0.2.0-alpha.29 with its rollback, and uninstall.
  - It also waited for hosted verification of this head on every supported platform.
  - alpha.30 closed the last known defect that could admit a wrong proof: a locked npm that Mise
    reported as missing resolved silently to Node's bundled npm.
- Not qualified by this beta:
  - the adopter journey on Windows, which no hosted job runs yet;
  - GitLab-hosted CI, GitLab publication and the Homebrew channel, which are not 0.2.0
    preconditions.
- Known open defects, none in a blocking class:
  - an absorbed-ref retirement preview that the reference-transaction hook then refuses;
  - no route to retire a legacy role ref that equals its standard successor;
  - unregistered Skill package directories that the portfolio report does not name;
  - jdx/mise#15363 upstream, which ETHOS refuses with its cause.

## [0.2.0-alpha.30] - 2026-11-04

### Changed

- Every ETHOS command now runs inside one invocation scope, which the entry point opens, so a
  command reads each immutable Git object and the running build once. Only `plan`, `status`,
  `adopt`, `land` and `publish` opened one before. The long-running MCP server keeps no invocation
  facts, since one process serves many requests. The 26 tests of
  `tests/unit/cli/test_contracts_land.py` start 9,415 native commands instead of 9,723.
- The Python lock moves Authlib to 1.9.3 and python-discovery to 1.9.2, the releases that had been
  public for 24 hours. `uv lock --upgrade --exclude-newer` applies that age, and a plain `uv lock`
  then removes the cutoff from the lock. filelock 4.2.8, platformdirs 4.14.4, python-discovery
  1.9.4 and virtualenv 21.15.5 were younger and wait for the next release.

### Fixed

- An executable that a declared Mise tool provides under its own name, such as `npm` for a locked
  `npm:npm`, must come from that tool's installed locked version, both from a locked tool and on a
  locked environment's PATH. Before, a locked npm that Mise reported as missing resolved silently
  to Node's bundled npm, so a gate could run the wrong tool and pass. A declared tool that nothing
  resolves yet blocks no other tool, so supply can still be provisioned on first use. A refusal now
  names the step that can help:
  - an earlier Mise, when Mise 2026.11.0 or later cannot use the lock's dependency graph in safe
    mode ([jdx/mise#15363](https://github.com/jdx/mise/issues/15363));
  - `mise trust`, for an untrusted root;
  - otherwise, `mise install --locked`.
- A failed save of the runtime inventory memo removes its temporary file after closing its stream,
  instead of leaving the file beside the memo.

### Security

- ETHOS reads the runtime inventory memo only from a directory and a file that the current user
  owns and that group and others cannot write. Before, another account that shared the data home
  through `XDG_DATA_HOME` could plant entries that made ETHOS reuse a digest for a payload file that
  account had changed. ETHOS creates the memo directory with mode `0700` and tightens an older,
  looser one when it next saves.
- The wheels and installed runtimes still ship npm 12.2.1 with the eight bundled advisories that
  the `0.2.0-alpha.22` entry lists, under the owner's acceptance until 2026-12-13 that the
  `0.2.0-alpha.29` entry describes. The release build's audit reports no other advisory.

## [0.2.0-alpha.29] - 2026-11-04

### Added

- Each release run attests the archives and wheels it publishes with GitHub artifact attestations
  before it creates the release, so `gh attestation verify` and Mise's GitHub backend can check
  that a file came from ETHOS's release workflow at its signed tag.
- A release run qualifies the prerelease it publishes on the adopter journey on macOS and Linux.
  Its `release-journey` job checks the platform archive against the release's checksums and build
  attestation, installs it through Mise, and proves a cold install, host-store pinning, hook
  binding, a full proof and status, an upgrade from the previous release with its rollback, and
  uninstall. A `journey_tag` dispatch runs the journey alone for an already published prerelease.
- A Change archives only after it cites every decision record that names it. When a record names
  an active Change's identifier in inline code, archive readiness, and with it the archive preview
  and the proof of that Change, reports `openspec_decision_uncited:<change>:<identity>` until one
  of the Change's artifacts contains the record's `DR-####` identity or file name.

### Changed

- A full executing proof runs its readiness gates, every gate that is neither a test nor a
  package gate, before it waits for its repository's proof slot and host load, and ends without
  waiting when one fails or when it plans no other gate. Its test and package gates still wait
  for admission, and no gate runs twice.
- The locked supply moves to the latest stable releases that ETHOS's constraints allow and that
  have been public for at least 24 hours, the release age Mise requires of its tools: Mise
  2026.10.25, which ETHOS's own repository now requires and its CI bootstraps with the release's
  official executable digests; Syft 1.56.0 and uv 0.13.7; and Cyclopts 5.3.3, FastMCP 4.1.6,
  filelock 4.2.7, python-discovery 1.9.1 and ty 0.0.96, with ETHOS now requiring Cyclopts 5.3.3,
  FastMCP 4.1.6, filelock 4.2.7 and uv 0.13.7 or later. The newer releases of Authlib, coverage,
  joserfc, python-discovery, uncalled-for and virtualenv were younger than that and wait for the
  next release.
- The shipped adopter CI model pins `jdx/mise-action` 5.2.6 by commit, which no longer hangs when
  a cache restore fails mid-download.
- GitHub runs ETHOS's full verification once for each published commit. A push to `main`, which
  moves only to the accepted commit that `dev`'s run already verifies, now runs only a
  `commit policy` job that admits the pushed range; host conformance, quality gates, external
  links, repository proof and package artifacts stay with `dev`'s run, as GitLab's `main` pipeline
  already leaves them to `dev`'s. A published commit costs about 320 GitHub job-minutes instead of
  about 640.
- A newer push of a proposal ref cancels the hosted run of its earlier push, whose head the ref no
  longer proposes: GitHub groups only proposal pushes by their ref, and GitLab cancels the jobs of
  the superseded proposal pipeline. No run of `dev`, `main`, a release, a manual dispatch or a pull
  or merge request is cancelled or queued, and a new `dev` commit no longer cancels a `dev`
  pipeline that still waits for its GitLab runner.
- The managed Ruff policy selects `docstring-extraneous-parameter` (`DOC102`), a preview rule enabled
  by its exact code, so a docstring that documents an argument its signature lacks fails lint in
  ETHOS and in every governed Python repository; `D417` already reports a missing one.
- Each hosted host conformance job uploads the stage timings of its package acceptance,
  `build/evidence/local-install/smoke.events.jsonl`, with its receipt `smoke.json`, also when the
  job fails.
- ETHOS's hosted CI installs the uv version that `.config/mise/config.toml` declares, read when
  the projections are compiled, instead of a version written into `.config/ci/pipeline.cue`. A uv
  upgrade edits the Mise configuration and its lock only.
- The shipped Vale policy ignores the directive lines of an Archify draft, `*.archify.md`: a line
  that starts with `@` and a directive name, such as `@source` or `@meta`, carries renderer
  arguments like paths and URLs, not prose. The rest of the draft keeps the full Markdown policy.
- ETHOS's module-layout gate refuses an identity forward in its product code: a module-level,
  undecorated function whose one statement returns a call to a function the module defines or
  imports, passing every parameter unchanged and nothing else. `openspec_base_command`, the last
  one, now owns the locked OpenSpec command resolution it used to forward to.
- A push of a proposal ref no longer runs GitHub's Windows on Arm host conformance, the slowest
  job of a proposal run: 71 minutes against 51 for the slowest native pair in run 41713822013.
  `dev`'s run of the landed commit, the proposal's exact commit, still runs it before the commit
  can be tagged, and so do pull requests and manual dispatches.

### Removed

- ETHOS's own docstring checker and its `docstrings` gate, `.config/checks/docstrings/policy.toml`
  and `src/ethos/repository/policy/docstrings/`. The managed Ruff policy's docstring rules check
  every module and package docstring and each docstring's summary and sections, and a CLI surface
  test requires help text for every registered command. Its weak-summary, reStructuredText-marker
  and unknown-section checks have no Ruff rule and are not replaced.
- ETHOS's optional local CI emulation, `tools/ci/ci_templates.py emulator-evidence` with `act` for
  GitHub and `gitlab-ci-local` for GitLab, and its policy fields. Hosted runs remain the only CI
  evidence, and the `ci_templates` gate keeps checking both projections.

### Fixed

- Prewrite no longer refuses a selected Change's write to a file directly in `openspec/changes/`,
  such as a guide or a template, as another Change's path. Only a file inside another Change's
  directory reports `openspec_change_path_mismatch`.
- Prewrite admits the deletion of a tracked file at a location the repository paradigm rejects,
  staged or not, instead of refusing it as a new file there with a repair that asks to move it. A
  path absent from the worktree is a creation only when neither the index nor `HEAD` tracks it, so
  a new file at such a location is still refused.
- The generated reference-transaction hook governs a ref deletion that Git reports without its old
  value, as `git branch -D`, `git update-ref -d` and the `packed-refs` side of every deletion of a
  packed ref do, by the ref's current value. `ethos lane retire absorbed-ref --apply` no longer
  fails for a packed ref, and the accepted branch's rules still refuse its deletion that way.
- Pre-commit admission checks staged Python with the shipped Ruff settings when a repository tracks
  no `.config/checks/ruff/ruff.toml`, as its `format_check` gate already does. It used to skip the
  check, so such a repository could commit Python that its own proof then refused.
- Proof admission reports `gate_runtime_missing:repository-python` when the worktree whose policy
  it compiles has no repository Python environment, with a remediation that runs the repository's
  bootstrap verb there. It used to report `proof_attestation_repository_policy_mismatch`, so a
  closeout whose candidate worktree had lost its `.venv` named no cause.
- The repository's Nox sessions no longer print markdown-it's debug records, which reached Nox's
  debug root logger whenever a session parsed Markdown in process: one local `nox -s prose` run
  printed about 27 MB of them. Warnings and errors from markdown-it still print.
- ETHOS's hosted CI waits up to about 13 seconds for Windows to release the Mise executable it
  has just verified before replacing the cached one with it, instead of failing the job with
  `WinError 32`, as `dev`'s Windows on Arm job did in GitHub run 41728732273.

### Security

- The wheels and installed runtimes ship uv 0.13.7, whose tagged lock builds it with rustls
  0.23.46, which fixes the four advisories that the `0.2.0-alpha.18` entry lists.
- They still ship npm 12.2.1, the latest release, with the eight bundled advisories that the
  `0.2.0-alpha.22` entry lists, and the product npm lock keeps the minimatch and glob overrides
  that it describes. The owner accepted those eight findings on 2026-11-03 for this exact npm
  release until 2026-12-13, or until an earlier npm release bundles the fixes, which then moves
  the pin. ETHOS installs with `npm ci --ignore-scripts`, so its installs never invoke npm's
  bundled `node-gyp`, the only user of the bundled undici, and the bundled `socks` client, the
  only user of ip-address, runs only behind a SOCKS proxy, which ETHOS does not configure. The
  release build's audit reports no other advisory.

## [0.2.0-alpha.28] - 2026-11-02

### Added

- After `ethos publish` moves a peer's accepted branch, its result names that peer's proposal refs
  whose tips the published head preserves (`absorbed_proposals`), and its next action is their exact
  retirement probe, so a landed lane's proposal is retired when its peer absorbs it rather than when
  someone remembers it. A peer whose proposals cannot be listed is named under
  `absorbed_proposals_unobserved`; the publication's own outcome does not change.

### Changed

- A conda package that a repository's Pixi manifest declares owns the executable of its package
  name, as a Mise tool owns its own: prewrite admits a touched carrier that runs it. The manifest is
  `pixi.toml`, or `[tool.pixi]` in `pyproject.toml` without one, and every conda dependency table
  counts, also under `target` and `feature`. PyPI dependencies, constraints and a package's other
  executables own nothing.
- ETHOS publishes with Git's sparse pack walk disabled, so a push of a batch of renamed directories
  sends only the objects its peer lacks.
- The locked supply moves to the latest stable releases that ETHOS's constraints allow: Vale 3.26.0,
  which the wheels carry; anyio 4.16.0, Authlib 1.9.2, FastMCP and fastmcp-slim 4.1.5 and
  platformdirs 4.14.3, with ETHOS now requiring anyio 4.16.0, FastMCP 4.1.5 and platformdirs 4.14.3
  or later; and globals 17.14.0, the minimatch override 11.0.4 and 27 npm packages within their
  declared ranges. The supported Python versions remain 3.12 through 3.14: `cel-expr-python` 0.1.3
  publishes no CPython 3.15 wheel or source distribution.

### Removed

- The source-only system contracts `system/formats.toml`, `system/routing.toml` and
  `system/evidence-boundaries.toml`, which nothing read beyond their presence, and their shipped
  schemas; `system/surfaces.toml` is the one system contract left.
- The repository gate `svg-format` and its `svg_lint` session: the shipped `source-format` gate
  already checks every authored SVG file with the same provider.

### Fixed

- `ethos lane archive-change` previews the archive it would apply: it simulates the archive and
  validates the merged specs strictly, as the proof does, so a requirement that the merge would push
  past OpenSpec's 500-character limit blocks the preview with
  `openspec_archived_requirement_invalid` instead of failing the apply.
- `ethos land` looks up its candidate authority under the Change that its admitted proof carries, so
  a lane that archived several Changes and was proved with an earlier one lands instead of refusing
  `proof_attestation_authority_binding_mismatch`.

### Security

- The wheels and installed runtimes still ship uv 0.13.6 and npm 12.2.1, the latest releases, with
  the bundled advisories that the `0.2.0-alpha.22` entry lists, and the product npm lock keeps the
  minimatch and glob overrides that it describes. The release build's audit reports no other
  advisory.

## [0.2.0-alpha.27] - 2026-11-02

### Changed

- Every wait ETHOS applies is a declared parameter. The paradigm declares each one's default, unit
  and bound: `timeout.gate_seconds` (600), `tool_seconds` (60), `git_seconds` (30),
  `git_history_seconds` (120), `probe_seconds` (15), `lock_seconds` (10), `download_seconds` (180),
  `request_seconds` (180) and `admission_seconds` (3,600), each bounded at ten times its default. A
  governed repository sets its own under `[paradigm.timeout]` in `.ethos/rules.toml`: a stricter
  value applies as given, and a looser one stays within the bound and states its reason in
  `[paradigm.timeout.reasons]` (GitLab issue #2).
- Every gate runs within a deadline: its declared `timeout_seconds`, at most 7,200, or else the
  repository's `timeout.gate_seconds`. The commands a gate runs no longer carry fixed timeouts of
  their own.
- Each `gate_completed` event records the gate's effective timeout and its source (`gate`,
  `repository` or `default`), and the proof summary lists every looser value with its reason under
  `parameter_deviations`.
- **Changed defaults:** Git observations wait 30 seconds instead of 10, a remote probe 30 instead of
  3, a native tool outside a gate 60 instead of 30, the staged-file format check 60 instead of 120,
  a version or identity probe 15 instead of 5 or 10, the ref-intent lock 10 instead of 1, a native
  supply preparation 180 instead of 30, and the custody lock 120 instead of 300.
- ETHOS's own source budget steps to 75,000 product and 95,000 test effective lines, one
  5,000-line step each under DR-0010, after the necessity review that the decision record cites.
- The repository paradigm declares the branch role names (`release`, `accepted`, `candidate`,
  `work_prefix`, `proposal_prefix`) in its `[branch]` table and keys the binding files by role
  (`[binding.files]`). ETHOS builds every binding carrier path, its version file, its changelog and
  every branch name from that declaration, and a newly formed repository starts on the declared
  accepted branch. An architecture check refuses a restated value in `src/`.

### Fixed

- A runner declaration in `.config/ci/runners.toml` now owns its identities in a hosted template
  that the CI projection declaration names as the source of one of that Forge's pipeline files, so
  patch admission and the repository semantic closure no longer refuse them as orphan consumers. A
  template projected into several Forges' pipelines needs each Forge's runner record, and a YAML
  file under `.config/ci/` that no projection names still owns nothing.

### Security

- The wheels and installed runtimes still ship uv 0.13.6 and npm 12.2.1, the latest releases, with
  the bundled advisories that the `0.2.0-alpha.22` entry lists, and the product npm lock keeps the
  minimatch and glob overrides that it describes. The release build's audit reports no other
  advisory.

## [0.2.0-alpha.26] - 2026-11-02

### Changed

- ETHOS proves its Python suite through the behavior probe it ships: `unit-architecture` is a
  provider row of `python_quality:behavior_report` bounded at 7,200 seconds, and the 95 percent
  floor is coverage's own `fail_under` in `.config/checks/coverage/coverage.toml`.
- The behavior probe applies a repository's `.config/checks/pytest/pytest.toml` and
  `.config/checks/coverage/coverage.toml` when they exist, takes its gate's `timeout_seconds`,
  keeps bytecode and Hypothesis storage in the attempt's scratch, and copies its reports to a
  native output root the runner names.
- ETHOS's suite sets its own process environment, loads a derandomized `proof` Hypothesis
  profile, and reports what each case crosses (`ethos.crossed`, `ethos.exceeds` in JUnit).
- Hosted CI sets `PYTEST_XDIST_AUTO_NUM_WORKERS`; hosted verification takes test and coverage
  figures from the probe's evidence and renders the Allure views itself.
- The locked supply moves to the latest stable releases of cachetools 7.2.8, filelock 4.2.6,
  nodeenv 1.12.0, platformdirs 4.14.2 and python-multipart 0.0.33; npm and Mise report nothing newer
  within ETHOS's constraints.
- A repository needs no Prettier, Taplo or Ruff carrier of its own: the formatters run on the
  settings ETHOS ships, and a carrier a repository keeps is still held to them (GitHub issue #20).
  `ethos repair` no longer writes formatter carriers.
- A root `package.json` `version` that equals `VERSION` is a checked projection of the one version
  source, so a repository can publish its npm package from the root.
- **Breaking for adopters:** every governed repository keeps `CONTRIBUTING.md` beside `AGENTS.md`
  and `README.md`, and a repository that tags releases keeps its license grant in `LICENSE`. ETHOS's
  own release-file list now derives from the paradigm. A sole publication peer may keep the remote
  name `git clone` gives it, which the paradigm declares as `origin`; with two or more peers, each
  remote takes its peer id.

### Removed

- **Breaking for contributors:** the `tests` and `coverage_floor` Nox sessions, the
  `coverage-floor` gate, `.config/checks/coverage/policy.toml`, `tools/ci/python_test_gate.py`
  with its ordering and bytecode helpers, and the `ETHOS_TEST_*` and
  `ETHOS_COVERAGE_LOCK_WAIT_SECONDS` runner variables. Run `ethos prove --gate unit-architecture`
  or pytest with `-c .config/checks/pytest/pytest.toml` instead.

### Fixed

- A tracked file that a lane deletes without staging the deletion is no longer quality input, so
  `ethos lane format` and every gate that reads candidate input stop refusing it with
  `authored_text_path_invalid`. A focused proof refused only because axes it did not select are
  unproven names `ethos prove --execute --json`, and a JavaScript test-scope refusal names each file
  that the runner did not enter or entered unselected.
- A failed or timed-out native command keeps its argv, exit status or bound and both whole
  streams: in a provider gate's diagnostic, in a refused Git text classification, which no longer
  reads as unobserved, and in the package acceptance's terminal evidence for a failed Mise call
  (GitHub issues #16 and #19). A provider gate whose deadline expires reports `gate_timeout` as
  unknown with its bound and elapsed seconds instead of `gate_provider_error` (GitLab issue #2).
- Hosted verification passes again on both peers: the Python test probe finds the native tools that
  ETHOS prepares outside mise, such as gitleaks for the staged-secret hook cases, after mise's own
  installs and before the host baseline. Report admission names each Allure result as allure-pytest
  does, so a parametrized case whose id contains `::` no longer refuses the attempt, and pytest
  writes every thread's stack at 540 seconds, before the 600-second bound ends a worker.
- Windows trust anchors and process listing use the operating system's security API and WMI in
  process through pywin32, which is now a direct Windows dependency, so ETHOS starts no PowerShell.
  On Windows a command's stderr is captured in a file, as its stdout already was, so a timed-out
  command no longer waits for a descendant that keeps its pipe open; every hosted Windows host
  proof hung there (GitHub issue #25).

### Security

- The wheels and installed runtimes still ship uv 0.13.6 and npm 12.2.1, the latest releases, with
  the bundled advisories that the `0.2.0-alpha.22` entry lists, and the product npm lock keeps the
  minimatch and glob overrides that it describes. The release build's audit reports no other
  advisory.

## [0.2.0-alpha.25] - 2026-11-01

### Changed

- The managed Ruff policy selects `unspecified-encoding` (`PLW1514`), a preview rule enabled by its
  exact code, so a text read or write without an explicit encoding fails lint in ETHOS and in every
  governed Python repository.

### Fixed

- ETHOS decodes every command's text output and encodes its text input as UTF-8 whatever the host
  locale, and every Python process it starts runs in UTF-8 mode (`-X utf8`). On a Windows host whose
  code page is 936, `ethos prove` stopped with "'gbk' codec can't decode byte 0x94" because Git's
  UTF-8 output was decoded with the locale. The Windows PowerShell observations write UTF-8 too.

### Security

- The wheels and installed runtimes still ship uv 0.13.6 and npm 12.2.1, the latest releases, with
  the bundled advisories that the `0.2.0-alpha.22` entry lists, and the product npm lock keeps the
  minimatch and glob overrides that it describes. The release build's audit reports no other
  advisory.

## [0.2.0-alpha.24] - 2026-10-31

### Fixed

- The release archive names its runtime directory with the first 16 hexadecimal digits of the
  runtime digest, as the host store does, so the Windows interpreter path inside the archive is 48
  characters instead of 96. Windows refused to start the interpreter under a deep install root,
  which GitLab Windows jobs reported as "exit status 6".
- `ethos lane archive-change --compensate` refuses while a recorded publication selects the archived
  head, and names the proposal retirement as the next action, instead of orphaning the proposal.
- The paradigm receives a byte-bound carrier that format selection freezes under a proof gate, as it
  receives vendored and generated files: the code ceiling does not measure it and its name keeps its
  form.

### Security

- The wheels and installed runtimes still ship uv 0.13.6 and npm 12.2.1, the latest releases, with
  the bundled advisories that the `0.2.0-alpha.22` entry lists, and the product npm lock keeps the
  minimatch and glob overrides that it describes. The release build's audit reports no other
  advisory.

## [0.2.0-alpha.23] - 2026-10-31

### Changed

- The code ceiling bounds every authored code file, not only Python: Go, Rust, JavaScript, JSX,
  TypeScript, TSX, CSS, SCSS, HTML, shell, PowerShell, batch and SQL files count too. An effective
  line holds a token that is not whitespace, a comment or documentation; directives, attributes
  and shebangs are code. Python keeps its syntax-tree measure, and every other language is
  measured with its Pygments lexer, now a declared dependency. Files that Git attributes mark
  vendored or generated are not measured. A file above the ceiling is split by semantic ownership
  into a subdirectory of modules.
- One language registry in the paradigm contract names each code language's suffixes and measure,
  the languages whose module file names the names obligation keeps, now including Rust, and the
  script languages. `[names] module_suffixes` and `[scripts] suffixes` are removed.
- The `[paradigm.size]` keys name the class: `code_effective_lines` and `document_nonblank_lines`.
  A declaration of the 0.2.0-alpha.22 keys `python_effective_lines` and `markdown_nonblank_lines`
  is reported with its rename, and the default stays in force. The size gap is now
  `repository_paradigm_code_size:<path>`.

### Security

- The wheels and installed runtimes still ship uv 0.13.6 and npm 12.2.1, the latest releases, with
  the bundled advisories that the `0.2.0-alpha.22` entry lists, and the product npm lock keeps the
  minimatch and glob overrides that it describes. The release build's audit reports no other
  advisory.

## [0.2.0-alpha.22] - 2026-10-31

### Changed

- The per-file ceilings default to 500: 500 effective lines for each tracked Python file and 500
  nonblank lines for each current authored Markdown document. A governed repository may declare
  its own value for its whole tree in `.ethos/rules.toml` `[paradigm.size]`. A lower value
  applies; a higher one applies up to the bound of 1000 when `[paradigm.size.reasons]` states
  why, and the paradigm report lists it as a deviation. A value equal to the default, a higher
  value without a reason, a value above the bound and an unknown key are gaps that leave the
  default in force. The retired `[quality.code_size]` table is still reported.
- The locked supply moves to the latest stable releases that ETHOS's constraints allow: mise
  2026.10.24, which ETHOS's own repository now requires and its CI bootstraps, Node 26.13.0, the
  first Node 26 LTS release, Python 3.14.10, OpenSpec 1.16.0, ESLint 10.14.0 and the latest stable
  releases in the Python lock, among them uv 0.13.6, Ruff 0.17.3, ty 0.0.95, pytest 9.2.0 and
  Pydantic 2.14.2. The supported Python versions remain 3.12 through 3.14. The CI model pins
  setup-uv 10.3.3 and jdx/mise-action 5.2.4 by commit.
- With OpenSpec 1.16.0, `openspec validate --strict`, which ETHOS runs, fails a scenario without a
  WHEN or GIVEN step or without a THEN step, and `openspec validate` fails when
  `openspec/config.yaml` cannot be read or is not valid YAML.

### Fixed

- Deletion admission admits a patch that replaces a vendored Python package with a dependency of
  the same name: when the root `pyproject.toml` declares such a dependency, imports of the deleted
  modules are not reported as `deleted_input` gaps. Deleting the project's own package, or a
  package that only a dependency of another name or a build requirement declares, still blocks.
- On Windows, publishing a native tool that ETHOS has just qualified no longer fails with
  `WinError 32` while Windows still holds the tool's image. The move into the cache is retried
  every 100 ms for up to 5 seconds, and a lasting refusal still fails.
- The dependency audit resolves npm findings through dependency cycles. A peer dependency, such as
  ESLint's on `@eslint-community/eslint-utils`, names each package in the other's `via`, and the
  audit refused every such cycle as `finding_identity_unavailable` instead of naming the advisory.
  A finding that reaches no advisory is still refused.

### Security

- The wheels and installed runtimes ship uv 0.13.6, the latest release, which still embeds rustls
  0.23.45 with the four advisories that the `0.2.0-alpha.18` entry lists.
- They also ship npm 12.2.1, the latest npm release. Its bundled undici 6.29.0 carries
  GHSA-4qv8-2p9j-2685 (medium), GHSA-xjj6-f33q-929c (high), GHSA-2m5v-pch6-74hx (high),
  GHSA-qrxm-fqhp-jwvm (high) and GHSA-9fm3-97px-rjf6 (medium); its bundled ip-address 10.7.2
  carries GHSA-rxp7-6hxx-x8q5 (medium); and its bundled minimatch 10.2.5 and glob 13.0.6 carry
  GHSA-g3hv-75wg-m249 and GHSA-3g3m-2fjr-6pw4 (both medium). undici 6.29.1, ip-address 10.7.4,
  minimatch 11.0.1 and glob 14.0.2 fix them, but no npm release bundles those yet, so the
  dependency gate reports them without blocking, as its policy requires while the bundling package
  is its latest release. The npm launcher package does not contain them.
- The product npm lock overrides minimatch with 11.0.3 and glob with 14.0.3, which fix
  GHSA-g3hv-75wg-m249 and GHSA-3g3m-2fjr-6pw4 outside npm's own bundle. The latest ESLint,
  `@eslint/config-array` and `test-exclude` still declare minimatch 10 and glob 13.

## [0.2.0-alpha.21] - 2026-10-30

### Added

- An adopter's proof reports the repository's semantic reference closure beside the audit reports:
  each latent gap with its carriers, without changing the proof verdict.
- Releases can serve `windows-arm64`. Its release leg builds and qualifies the x64 runtime on a
  Windows ARM64 host, which runs it through Windows on Arm's emulation, and the release declares
  that leg's archive for the platform. No `windows-arm64` wheel is published: `cel-expr-python`
  ships no native build for it. Host conformance and the release add a `windows-11-arm` leg.

### Changed

- Commands that run inside double-quoted `$(…)` and backticks are now read. A patch that touches
  such a carrier must own them, as it owns the carrier's other commands.
- Each release leg declares the host platform it qualifies, and its archive and Mise platform are
  named for that host. Only a host that runs the runtime natively publishes a wheel or counts as a
  required platform.
- The npm launcher under `distributions/npm` is a standalone package, no longer a workspace of the
  root package, so `package-lock.json` records no product version and a release changes no lock.
  The version check refuses a lock that records it.

### Fixed

- Closeout under an `accepted_ff` release mirror creates an absent release branch at the candidate
  head in the same transaction, so a repository formed by `ethos adopt --create` can make its first
  release. It no longer reports the absent branch as `release_mirror_diverged`.
- An x64 interpreter that Windows on Arm emulates now selects its own runtime and builds an
  installable wheel. CPython on Windows reports the native CPU, so ETHOS reads the machine the
  interpreter executes from its build platform. Every native host observes the same values as
  before.
- Prewrite no longer refuses a governed repository's patch for references that no executor runs or
  that a declaration supplies:
  - Shell lines follow POSIX nesting. Quotes pair within each `$(…)`, backtick and `$((…))`,
    arithmetic words are values, and a command word that an expansion forms, such as `$PYTHON`,
    names no executable.
  - In documentation, `<name>` placeholders and `--flag a|b|c` synopses are values.
  - A CI step that the retention record keeps is owned as a whole, whatever shell it is written
    for, until its text changes.
  - Each tool that `.config/mise/config.toml` declares owns its executable: its `rename_exe`,
    otherwise the last segment of its identity. Companions such as `rustup` stay unowned.
  - Each top-level package in the tree, such as `.githooks/_hook`, is first-party.

### Security

- The wheels and installed runtimes still ship uv 0.13.5, whose embedded rustls 0.23.45 carries the
  four advisories that the `0.2.0-alpha.18` entry lists; uv 0.13.6, the latest release, embeds the
  same rustls.
- They also ship npm 12.2.1, the latest npm release. Its bundled undici 6.29.0 carries
  GHSA-4qv8-2p9j-2685 (medium), GHSA-xjj6-f33q-929c (high), GHSA-2m5v-pch6-74hx (high),
  GHSA-qrxm-fqhp-jwvm (high) and GHSA-9fm3-97px-rjf6 (medium), and its bundled ip-address 10.7.2
  carries GHSA-rxp7-6hxx-x8q5 (medium). undici 6.29.1 and ip-address 10.7.4 fix them, but no npm
  release bundles those yet, so the dependency gate reports them without blocking, as its policy
  requires while the bundling package is its latest release. The npm launcher package does not
  contain them.

## [0.2.0-alpha.20] - 2026-10-30

### Fixed

- Prewrite no longer refuses a governed repository's patch for references the repository owns or
  never makes:
  - Only authored command names declare commands. A Cyclopts application's variable name, a
    computed `name=` and another framework's decorators declare none, and a single word in prose
    is a term rather than an invocation.
  - Package-relative imports stay inside their package.
  - The repository's own modules, at its root or under `src/`, are first-party without a
    hard-coded module list, and a governed repository owns the product's import package.
  - Pixi environments map declared distributions to their modules, as `.venv` does.
  - A patch admission now reports every refused reference, not only the first.

### Security

- The wheels and installed runtimes still ship uv 0.13.5, whose embedded rustls 0.23.45 carries the
  four advisories that the `0.2.0-alpha.18` entry lists; uv 0.13.6, the latest release, embeds the
  same rustls.
- They also ship npm 12.2.1, the latest npm release. Its bundled undici 6.29.0 carries
  GHSA-4qv8-2p9j-2685 (medium), GHSA-xjj6-f33q-929c (high), GHSA-2m5v-pch6-74hx (high),
  GHSA-qrxm-fqhp-jwvm (high) and GHSA-9fm3-97px-rjf6 (medium), and its bundled ip-address 10.7.2
  carries GHSA-rxp7-6hxx-x8q5 (medium). undici 6.29.1 and ip-address 10.7.4 fix them, but no npm
  release bundles those yet, so the dependency gate reports them without blocking, as its policy
  requires while the bundling package is its latest release. The npm launcher package does not
  contain them.

## [0.2.0-alpha.19] - 2026-10-29

### Changed

- Git hooks start the ETHOS runtime only for a reference transaction's prepared state. The
  generated launcher exits in `sh` for the preparing, committed and aborted states, which ETHOS
  never governed, so `git update-ref` starts the runtime once instead of three times and a commit
  only for its prepared transactions. A repository gets the new launcher when it reinstalls hooks
  with `ethos hook install`; the launchers of earlier runtimes keep working until then.
- ETHOS judges its own tree by the obligations it ships for every repository. The packaged
  `system/gates.toml` holds only those obligations, declared as every repository runs them, and
  ETHOS declares its own gates in `system/repository-gates.toml`, which its profile names. A
  repository's obligations no longer depend on its registry path or its history.
- The shared Python static floor follows the import-sorting values that a repository's native Ruff
  configuration declares.

### Fixed

- A focused `ethos prove --gate` compiles code obligations only when a selected gate verifies code.
  A gate whose own implementation is repository code, as ETHOS's providers are in its own tree, no
  longer makes a document or link check require the code floor.
- A provider failure reported from a nested command scope ends only that scope's commands. One
  failing gate no longer stops its sibling gates with `process_cancelled`; cancelling the proof
  still ends every gate's commands.
- A gate that declares no native outputs runs without a native output root. Its commands no longer
  inherit `ETHOS_NATIVE_OUTPUT_DIR` and `ETHOS_NATIVE_OBSERVER_REQUIREMENT` from an enclosing
  attempt, such as a tests session that runs gates, so they cannot write into that attempt's root.

### Security

- The product npm lock overrides markdownlint-cli2's re2js 2.8.6, which markdownlint 0.42.0 pins
  exactly, with 2.8.8. re2js before 2.8.7 matches lookbehind assertions in quadratic time
  (GHSA-gg6h-894w-4m9c, high, published on 2026-10-28), and markdownlint 0.42.0 and
  markdownlint-cli2 0.24.0 are their latest releases. `v0.2.0-alpha.18` ships re2js 2.8.6 in the
  Node supply of its markdown lint gate.
- The wheels and installed runtimes still ship uv 0.13.5, whose embedded rustls 0.23.45 carries the
  four advisories that the `0.2.0-alpha.18` entry lists; uv 0.13.6, the latest release, embeds the
  same rustls.
- They also ship npm 12.2.1, the latest npm release. Its bundled undici 6.29.0 carries
  GHSA-4qv8-2p9j-2685 (medium) and GHSA-xjj6-f33q-929c (high), which the `0.2.0-alpha.16` entry
  lists, and GHSA-2m5v-pch6-74hx and GHSA-qrxm-fqhp-jwvm (high) and GHSA-9fm3-97px-rjf6 (medium),
  published on 2026-10-27; its bundled ip-address 10.7.2 carries GHSA-rxp7-6hxx-x8q5 (medium).
  undici 6.29.1 and ip-address 10.7.4 fix them, but no npm release bundles those yet, so the
  dependency gate reports them without blocking, as its policy requires while the bundling package
  is its latest release. The npm launcher package does not contain them. `v0.2.0-alpha.17` and
  `v0.2.0-alpha.18` ship the same npm; their entries do not list the three advisories published on
  2026-10-27.

## [0.2.0-alpha.18] - 2026-10-29

### Changed

- Eleven governance policy documents that no higher owner named give back their statements: the
  covered ones become links to their owners, twelve unique obligations become requirements of the
  repository-governance, distribution, adapters and quality specifications, and two new guides take
  the independent-verification and release procedures. The proof-hosts specification, the rules
  index, the module layout rule, the system contract headers and the documentation metadata no
  longer cite removed behavior.
- A Change needs one complete proof instead of two. `ethos lane archive-change` no longer requires
  a proof of the pre-archive head; the archived head is proved once, and landing requires that
  proof. When that proof fails, `ethos lane archive-change --compensate` returns the unlanded
  archive to its exact pre-archive head.

### Removed

- The hidden `ethos hook pre-push` command is gone; Git's native pre-push hook is the one push
  admission. When a push waits for accepted closeout, the hook's report names the exact
  `ethos land --closeout` command, as the removed command did.
- `ethos prove` no longer accepts `--execution-root`, and its proof execution carrier is gone. The
  archive command commits a staged archive, and the archived head is proved in the Work Lane.
- The wheel no longer ships the five retired policy documents. `ethos context` serves the matching
  sections of the Product Design Contract and the release rules in their place, with the same reader
  roles.

### Fixed

- Host-store retention no longer removes an installation that a repository is about to select. A
  repository now holds its runtime selection lock from the pin that records it as a consumer until
  its selectors name what it pinned, and retention keeps every consumer whose lock is held. It takes
  that lock only in a repository with ETHOS state, so it creates nothing in one without. Before,
  a retention that another repository ran inside that window released the record, and a later one
  removed the installation that the repository's `CURRENT` then named, so its commands failed with
  `hook_runtime_manifest_invalid` or `hook_runtime_current_target_invalid`. Repositories that still
  run an earlier release keep the old window until they rebind.
- Python reference observation follows import aliases, from-imports, lexical scope and program
  point. A local named like a module no longer invents a consumer, a later assignment no longer
  replaces an earlier read, and a command constant that nothing runs is no longer a consumer. A
  sink chosen by dynamic lookup makes its file unknown instead of passing as evaluated.
- Dockerfile and Containerfile `ENV` and `ARG` names, and Compose service environments, declare
  the runtime values that maintained code reads.
- Native tools no longer report a moved configuration carrier as ambiguous while the index still
  lists its deleted previous path.
- Reference admission accepts the executables that the local publication commands in
  `.ethos/release.toml` invoke.
- An active Change's validation repair is no longer refused because another active Change drifted
  from its template.

### Security

- The wheels and installed runtimes ship uv 0.13.5 as a production dependency, which ETHOS runs to
  build runtime environments and Python gates. Its embedded rustls 0.23.45 carries four advisories
  published on 2026-10-27: GHSA-c8m5-c952-6cm4 (medium) and GHSA-vp88-798v-h67f,
  GHSA-w44r-93j7-qv28 and GHSA-h2v8-394m-p7vv (low). rustls 0.23.46 fixes them, but no uv release
  embeds it yet; the latest, 0.13.6, still embeds 0.23.45. The dependency gate audits the locked
  Python and Node packages, not the crates inside a package's binary, so it does not report them.
  `v0.2.0-alpha.17` ships the same uv.

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
