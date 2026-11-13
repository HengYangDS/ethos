# Design

The base is a rule: an obligation whose rule is the same for every governed repository, selected by
the carriers it authors and the values it declares, is owned once by ETHOS in an existing owner and
supplied by the product that judges; gates and values that express a repository's purpose stay the
repository's. Thirteen Changes reach the end state below along TP's batch 8 and its Immediate
Dependency 1. Three are release-candidate work before the freeze: `ci-economy` (hosted CI near 40
minutes on GitHub and under 15 on GitLab), rc's C1 to C4 with C4 split in two and the adopter bump
(one pin line in each of the eleven adopters outside the two deferred families), and an
installed-hook step in `local-install-smoke`. Ten are 0.3.0 work against DR-0022, none during the
soak: three reporting floor families, one arming Change each, a release-time record of reach and
retirement, CI extension points, one release operation and default verb bodies. A Change closes on
its source acceptance; TP reads its landing effects and adopter deletions back through product
reports, and the 0.3.0 Changes wait for a necessity review or rc's reductions.

Line references are to `dev` at `aa9f85d51`. PDC, TP, rc, pf, RG, RP, Q, DS and adapters are the
product design contract, the terminal plan, the archived `rc-plan` and `product-form-plan` designs
and the `repository-governance`, `repository-paradigm`, `quality`, `distribution` and `adapters`
specifications. AR is the owner-approved end-state design (revision 6.9, ignored scratch
`build/runtime/work/architecture-realization/design.md`) and "the 10-31 design" is
`build/runtime/work/shared-ownership-design/design.md`; both are evidence only. Forge figures are
condensed with their dates (survey of 2026-11-13); "packet N" is item N of the hosted CI evidence
that this Change moves to `docs/research/foundations/hosted-ci.md`.
Adopters appear by shape and count; each adopter's named list goes to its lane owner before this
Change archives. Inference is marked.

## Base

The base is every obligation whose rule is the same for every governed repository, a function of
the carriers it authors and the values it declares, owned once by ETHOS and supplied by the product
that judges (PDC:22-23, 332-340; DR-0017:45-57; DR-0012:45-56; RG:5166-5173). Its owners exist:
the packaged `system/gates.toml`, the paradigm contract, the operations catalog, the shipped CI
template and the Skill. No carrier is named "base" or "floor"; this design says "shared floor" for
the shipped gates (RG:5172) and "shared obligations" for the whole. Out are the gates and values
that express a repository's purpose, which ETHOS runs and attests (DR-0017:49-50), and a subset's
commonality until DR-0012's revisit (DR-0012:85; DR-0017:77-78), since a rule sinks by meaning, not
by code similarity (DR-0017:64-65). The route is TP's Immediate Dependency 1 (TP:71-75) and batch
8, which exits when "no adopter compatibility carrier or copied state machine is required"
(TP:372-373); this Change places its order there, in no new TP section. The fourteen families:

| #   | Family                     | Owner and placement                                     |
| --- | -------------------------- | ------------------------------------------------------- |
| 1   | Hooks and commit admission | shipped; D10 admission jobs; Ch10 installed-hook step   |
| 2   | Lane lifecycle             | shipped kernel; Ch5's hook-tree and source-path reports |
| 3   | Documentation layout       | shipped; adopter copies retire in the first step (D12)  |
| 4   | Formatting and spacing     | shipped; adopter copies retire in the first step (D12)  |
| 5   | OpenSpec                   | shipped; common rules repaired inside the bump (D4)     |
| 6   | Supply and locks           | Ch2 pin; D1 supply owners; Ch3 audits; Ch5 tools        |
| 7   | Security                   | Ch3, armed by Ch11; D10 hardening; owner tasks          |
| 8   | CI                         | Ch1 for ETHOS; Ch7 for the template                     |
| 9   | Release and publication    | Ch2 (rc's chain); Ch8                                   |
| 10  | Metrics                    | rc B3; pf B13 and B14; CI figures read on demand (D8)   |
| 11  | Entry documents and verbs  | Ch9 (D7)                                                |
| 12  | Language quality           | Ch4, armed by Ch12, with a MODIFIED Q:98-118            |
| 13  | Adoption exit              | D7                                                      |
| 14  | Obligation effectiveness   | Ch6 attests reach and retirement (D8)                   |

## End State

When every Change and delivery item is done:

- **Shipped registry**, by selecting fact: today's `docs-registry`, `markdown-links`,
  `markdown-lint` and `prose` (`*.md`), `openspec`, `config-quality`, `source-format`, `schemas`
  and `skills`; then `secrets` (every authored path), `dependency-vulnerabilities` (lockfiles,
  `full` only), static and behavior gates per language suffix with `module-layout`'s shared rules,
  `github-workflow-syntax` (GitHub workflow files), `asset-validation` (PNG), `source-budget` (a
  declared `[source_budget]`), `commit-ranges`, `generated-artifacts` and `repository-audit` (every
  governed repository) and the projection check (two forge files and a model, RP:627-634).
  `external-links` runs as a hosted observation in no proof set.
- **ETHOS's registry**: `product-boundary`, `build`, `local-install-smoke` with its installed-hook
  step, `release-sbom`, `format-selection`, and the supply-image binding and forge-surface checks,
  each with a one-line reason; `module-layout`'s ETHOS-specific dimensions become ETHOS's values.
- **ETHOS's `tools/`**: the journeys and assembly in `tools/ci/delivery/` (rc's B2 and B9; Change 8
  takes the generic part), `toolchain/` (ETHOS's bootstrap, run by no adopter after R9),
  `hosted_observation.py` (rc A11), `hosted_verification.py` (Q, until rc's CI carriers), the two
  `release-sbom` modules, `format_selection.py`, `supply_image.py`, `openspec_runtime_hook.py` and
  the Nox sessions; `dependency_audit.py` moves in Change 3, `dependency_hygiene.py` and
  `repository_hygiene.py` in Change 4, and `ci_templates.py`, `ci_projection.py:38-205` and
  `architecture_projection.py` in Change 5.
- **Every adopter** keeps its domain gates and values, its CUE domain jobs on the template, one pin
  line, its own task bodies, its purpose beside formation's AGENTS.md pointer, and OpenSpec's common
  rules, the one product-owned copy, which the bump repairs. The film repositories' shared rules
  stay with their tooling library: AR reserves such a pack until a second repository asks
  (AR:785-788), and none has shown a need one owner cannot carry (DR-0017:77-78).

| Shape                   | Count | Beyond the common list                                    |
| ----------------------- | ----- | --------------------------------------------------------- |
| Go CLI                  | 1     | Go and dependency-scanner additions; release builds       |
| Python service          | 2     | stricter lint, types and coverage values; domain checks   |
| Python, deferred family | 2     | domain and agent operations; migration deferred           |
| JavaScript package      | 1     | lint, type and dead-code additions; npm publication       |
| Documentation           | 3     | content and edition publication; one pin from `adopt`     |
| Film                    | 4     | film content; one shared tooling library; one `adopt` pin |

The two deferred families' migration and cleanup wait: owner, each repository's owner; next action,
the first step's preview on their current runtime; review date, 2026-11-27. Their analysis is in
scope, and their pins and other items are delivery items of their own migrations.

## Context

- **Today's shared floor.** `system/gates.toml` ships 9 gates, 7 selected by `required_for_paths`;
  composition adds each where authored paths match, to both proof sets, refuses a conflicting
  execution and imports only providers
  (`src/ethos/repository/policy/quality/gate_composition.py:29-73`). Python's floor runs
  `ruff --isolated --select E,F,B,I,UP` (`src/ethos/adapters/gates/python_quality.py:75-93`), Go's
  `gofmt -l` and `go vet` (`code_quality.py:247`, `:253`); the staged secret scan runs only where a
  Gitleaks policy exists (`src/ethos/adapters/repo/hook/admission.py:230-236`), from `PATH`.
- **What ETHOS keeps.** 27 private gates, 11 in `default` and 26 in `full`, in
  `system/repository-gates.toml` (`.ethos/profile.toml:7`), among them a redeclared `skills`
  (`:78-93`) and `external-links` in no set; Q:10-16 and RG:893-897 call the packaged registry the
  only gate declaration, while PDC:325-327 allows a repository's own. Its CI bypasses the template
  (`.config/checks/ci-projection/policy.toml:43-46`), and its release lives in `tools/ci/delivery/`
  (5,840 lines) and `pipeline.cue:535`.
- **Thirteen adopters**, read-only on 2026-11-13, by the shapes of the End State table. Pins: six
  hand tables (five on `dev`, three at beta.9, one at alpha.29 and one at alpha.27, and one on a
  deferred family's work branch, which its own invocations bypass), six repositories with none
  (a Python service, the Go CLI, the JavaScript package, the two repositories that formation made
  and a deferred family), and one Python service whose CI builds ETHOS from a source commit and runs
  ETHOS's `tools/ci/toolchain`. Six render or check CI with their own code: the Go CLI, both Python
  services, the JavaScript package and both deferred families. 19 gates in seven profiles name
  `ethos.*` providers, and three of them no longer resolve. Only the deferred families rebuild hooks
  and lane lifecycle, and four adopters (the two formation-made repositories and both deferred
  families) fail the OpenSpec common-rule prefix.
- **What upgrades cost.** `adopt` writes no pin; 40 archived `rebind-ethos-*` Changes in seven
  adopters from 10-25 to 11-12 (pf:23-25 counted 39 in eight), and supply bumps repeat per adopter.
  beta.7 to beta.9 were dispatched from `main` (`releaseRun` in each tag's `pipeline.cue`) after
  rc's `attested-main` ends at beta.6, so they fall in no class (rc:466-470).
- **What hosted CI costs** (forge survey of 30 dev pushes, 11-07 to 11-12). A GitHub run takes 68.9
  minutes at the median (p90 74.4) and a GitLab pipeline 40.1 (p90 114.7). The emulated Windows on
  Arm leg takes 68.5 and four Windows legs run per push (`pipeline.cue:322-336`), though DR-0021
  declares no Windows journey (DR-0021:44-46); then comes `quality gates` (37.8), mostly one test
  gate that decides coverage in one execution (Q:125-126). The full set runs twice on hosted Linux
  arm64 (`pipeline.cue:381`, `:726`), yet GitLab's loaded guest found a race that its proposal
  pipeline passed (hosted-CI evidence of 2026-11-04). ETHOS and nine adopters share one GitHub
  owner, so one macOS pool (packet 23, unofficial).

## Goals / Non-Goals

Goals: eight criteria, each with its verifier and its status at `aa9f85d51`.

1. **Facts select the shared floor** (PDC:332-340; RG:5166-5173); shape fixtures (Python, Go,
   JavaScript, polyglot, documentation and media, package-only; each with one and with two peers)
   give the verdicts ETHOS gets for the same carriers (Q:1681-1686). Partly met: Markdown,
   configuration and OpenSpec.
2. **ETHOS consumes what it ships** (PDC:325-327, 588); its registry holds only ETHOS-domain gates,
   each with a reason. Not met: 27 private gates.
3. **No candidate lowers the floor, and additions run in the same gate** (RG:5171-5172;
   PDC:266-267). Half met: Ruff runs isolated, and stricter policy runs as a separate gate.
4. **An upgrade is one reviewed pin change** (PDC:33-34; pf:41); a release that edits a common
   OpenSpec rule bumps an adopter in one Change. Not met: no pin writer, six hand tables.
5. **No adopter carries a copy of a shared mechanism** (PDC:62-63; RG:5175-5179); no duplicate-owner
   or provider gap and no source-path, hook-tree, branch-role or CI-generator report remains, and a
   copy that no report sees is read back from the adopter's own archived Change. Not met.
6. **Extension is declared, not generated** (PDC:68-69, 477-478); no CI-generator report remains.
   Not met: six adopters.
7. **Shared obligations' reach and retirement are attested each release** (PDC:35-36, 75-76; the
   owner on 11-01, AR:22); per obligation, its reach, state, duplicate-owner gaps and read-back
   deletions. Not met.
8. **Hosted CI proves what the local proof cannot, once per plane**
   (`docs/architecture/gate-runner.md:43-44`; PDC:498-502). Not met.

Non-Goals:

- No adopter's domain logic moves and no adopter implementation is copied (TP:94-95); floors carry
  obligations, not ETHOS's tools or thresholds (TP:74-75); ETHOS owns no adopter's toolchain
  (pf:48-49). ETHOS's tracked text names no adopter and carries no other repository's internals.
- No carrier, schema, record or state without PDC:347-357's three answers.
- No hosted service, no public per-adopter data, no channel that sends adopters' proof events to
  ETHOS, and no forge read for metrics in `status` or the release path.
- No Change edits a forge setting: an owner action is a task of the Change whose acceptance needs
  it, or a delivery item in TP.
- No SLSA level is claimed (pf:50), no 0.3.0 Change lands during the soak, and this Change
  implements nothing: it changes TP's order and this design, with `skip_specs: true`.

## Decisions

1. **Facts select the shared floor.** The packaged registry gains provider gates selected by facts,
   and composition does the rest with one new rule, carried by Change 3 with a split of
   `select_gate_declaration` (pinned at 25): a shipped gate whose closure is not offline joins only
   `full`, since a re-validated narrower `default` holds only offline source checks
   (`src/ethos/contracts/gates.py:303-314`, `:372-390`). Adopters' sets are equal today
   (`src/ethos/repository/profile.py:202-205`), so their `default` becomes narrower than `full`
   for the first time, as plain `prove` shows; regressions cover equal and unequal sets.
   - Facts: `secrets`, every authored path; `dependency-vulnerabilities`, lockfiles; language gates,
     the paradigm's suffixes (`src/ethos/contracts/paradigm/paradigm.toml:228-323`);
     `github-workflow-syntax`, workflow files; `asset-validation`, PNG; the projection check,
     RP:627-634's two forge files and a model; the product mode, the distribution name
     (DR-0017:75-76); `source-budget`, a declared `[source_budget]`, which no adopter has. No
     declaration selects a shared gate.
   - Supply: Gitleaks from native supply
     (`src/ethos/adapters/repo/runtime/materialization/native_supply.py:41-48`), materialized at
     install so tree and staged scans run offline under one owner; actionlint and ShellCheck join
     it in Change 5 (ETHOS's own today, `.config/mise/config.toml:12`; `pyproject.toml:56`); Go's
     tools from the repository's toolchain; uv and npm audits from its lock, `uv.lock` without an
     auditor while uv's is a preview (`tools/ci/dependency_audit.py:122-128`; PDC:444-449); ty,
     import-linter, deptry, golangci-lint and other scanners only as additions.
   - Platforms: macOS and Linux are claimed; Windows reports without blocking, a named absence
     (PDC:579-582). A new gate field says so: `policy`, `profile` and proof sets hold for every host
     (`gates.py:132-168`) and missing supply does not pass (`gate-runner.md:42-43`); the gate
     contract owns it until Windows is qualified.
   - Lifecycle: a floor lands reporting, as latent gaps that leave the verdict unchanged
     (RG:5989-5993); an arming Change per family names the release that blocks (Changes 11 to 13),
     in 0.3.0 one `beta` channel move (DR-0022:47-51; inference), after a run on every adopter on
     the releasing host with an owner per finding and its seconds measured per runner class.
   - Repairs: allowlists, baselines and ignore files are relaxations recorded with a reason at the
     paradigm's carriers (`paradigm.toml:508-516`) and judged on the trusted base tree; record roots
     and archived Changes report older content only; a lockfile class without an auditor is a
     non-blocking gap that no arming Change arms; an advisory without a fix takes an expiring
     acceptance (`dependency_acceptance.py:67`); staged scans and range admission replace history
     scans.
   - Ownership: a repository names shipped gates by id only. The paradigm reports, as latent gaps
     with one `next`, a gate naming an `ethos.*` provider (repair: the shipped id, or deletion where
     composition adds it) and a gate running a shipped gate's tool on its carriers (duplicate
     owner); a profile naming a moved provider fails with a named gap before any gate runs, and a
     provider that an adopter gate needs either ships as a gate or gets a declared public name.
     Until Change 3 lands, each batch head's adopter pre-check catches a moved provider that an
     adopter profile names, and that adopter repairs it in its bump lane.
2. **ETHOS consumes what it ships.** By DR-0017's test, ETHOS's 27 gates split as below (inference
   from their definitions); ETHOS's moves are moves, and only adopter deletions count as retirement:
   - Shipped, or retired as duplicates (22): `secrets` and `dependency-vulnerabilities` (Change 3);
     `code-static`, `unit-architecture`, `javascript-tests`, `ruff`, `python-types`,
     `import-boundaries`, `dependency-hygiene`, `repository-hygiene`, `javascript-lint` and
     `module-layout`, whose language-neutral rules are shared and whose ETHOS dimensions become
     values (Change 4); `github-workflow-syntax`, `ci-projection`, `architecture-projection`,
     `external-links`, `asset-validation`, `commit-ranges`, `generated-artifacts`,
     `repository-audit`, `skills` and `source-budget` (Change 5).
   - ETHOS-domain (5): `product-boundary`, `build`, `local-install-smoke`, `release-sbom` and
     `format-selection`, joined in Change 5 by the supply-image binding and forge-surface checks
     (`tools/ci/ci_projection.py:248-302`), which lose their caller with `ci_templates.py`.
3. **One gate, two layers.** Each shipped language gate runs its floor rules under the product's
   locked tool, isolated (`python_quality.py:75-93`), and a repository's additions under its own
   locked tool, with its `.config/checks/<tool>/` configuration (PDC:324-325) read from the trusted
   base tree, since trusted prior policy judges an unaccepted target (PDC:266-267). A `lint.select`
   that contains the floor rules is a legal addition, so a policy that selects every rule applies;
   one that drops a floor rule is reported, and the rule still runs. An ETHOS Ruff bump changes
   only the floor rules and is named in release notes. A tightening applies at once and a
   relaxation only after it lands alone; so do the floor's tree-read target and import style
   (`python_target.py:1-11`) and an ETHOS pin or addition-tool version below the base tree's,
   since in hosted CI the candidate's lock picks the judge (`.config/ci/verification.cue:40`).
   The trusted base tree is an explicit `prove` input that each hosted event supplies (a push's
   previous head, a pull request's `base.sha`, a merge request's diff base with the target
   fetched), refused as `unknown` when absent; until Change 4 adds it, additions are judged locally
   only (`tools/ci/hosted_verification.py:184-193`).
4. **Delivery: close `attested-main`, keep rc's chain and the RC gate.** C1 followed
   `release-provenance` only so that its release would have a class, which beta.7 to beta.9 already
   lack (Context), and that edge closed a cycle with `release-provenance`'s place after B6 and B7
   (rc:125-126, 140-148, 518-519). So `attested-main` closes by rule at the last main-dispatched
   release, each qualified by DR-0018's digest binding and a mismatch making it `checksum`.
   `release-provenance` stays whole, precedes B11 (rc:150-151) and records that cutoff in C1's class
   data as the class's tested exit (PDC:88-89). C1 checks from the forge each main-dispatched
   release that exists at its readiness; each later one's release Change repeats the check.
   - Order: Change 1 first among the `pipeline.cue` editors, on R's critical path; C1; C2, C3 and
     C4's first half; the adopter bump (pf:118-123; working name `adopter-bump`) after C3; C4's
     second half a batch later; rc B3 after C1; B2, B4, B6, B7; C5 after R9's migration;
     `release-provenance`; B11; C6 after C4's first half and B6, whose rehearsal runs its leg
     (rc:508-511); all before the freeze.
   - C4 becomes two rc Changes. `release-identity` (working name; +60/+60/0) carries the readers of
     both identity schemas, the identity binding and the attestation of `SHA256SUMS`, which C4 and
     C6 read (rc:601-603, 611) and today's step omits (`pipeline.cue:529-531`).
     `release-acceptance` (+60/+50/0) carries the publish refusal and `release accept` a batch
     later, so no adopter takes two breaking steps in R (rc:601-607); C6 follows the first, keeping
     Homebrew's chance for 0.2.0 (DR-0021:47-50). The contract step, dropping the old reader, has
     owner 97f828 and its exit at the first 0.3.0 build; the soak's bump is to the release carrying
     the second. TP records the amendments of rc:127-128, rc:143, rc:574-575 and pf:124-125.
   - R, a TP milestone: the first weekly batch after beta.10 with C1, C2, C3, `release-identity` and
     the bump. The soak then starts at least two releases after beta.10, so rc's 11-18 to 11-25
     estimate moves (rc:240-242; inference).
   - The RC gate holds. `secret-scan-supply` stays an RC item as rc designed it (locked supply,
     unarmed report; rc:130-131). R9, and so C5's prerequisite, covers the eleven adopters outside
     the deferred families (rc:619), whose own pins are delivery items of their migrations. C3's
     `adopt` writes the pin for the two repositories that formation made, and the Python service
     whose CI builds ETHOS from source installs the pinned release instead and stops running ETHOS's
     `tools/ci/toolchain`. If its owner shows that infeasible before the freeze, the exception, its
     reason, the narrowed 0.2.0 claim and its exit (Change 7) go to the owner and TP.
   - The bump's preview and apply repair OpenSpec's common rules
     (`src/ethos/repository/paradigm/openspec.py:66-75`), the one product-owned copy left; task
     bodies are the repository's (decision 7). A regression shows a release that edits a common rule
     bumping an adopter in one Change.
   - Rollback: a `ROLLBACK` selector may name a runtime outside the repository store
     (`src/ethos/adapters/repo/runtime/selection.py:160-169`), which `hook install --runtime` then
     refuses (`hook_runtime_manifest_invalid`). C2, which writes rollback receipts (rc:594-597),
     proves a rollback runnable before writing `ROLLBACK`; `status` reports an unrunnable one with
     one repair `next`, and B8's journey (rc:474-481) gains the case.
   - `release-provenance`'s source acceptance is its own (the projection carries the environment and
     `env` inputs; the guide's step 5 changes, `docs/guides/release-and-publication.md:23`); its
     first release's verification is a delivery item. 0.2.0 keeps lane-built supply binding
     (Q:2024-2034) and adds R8(b)'s image attestation to `supply-image`; dev-only provenance
     (rc:127-128) moves to 0.3.0. `queue: max` for release runs (packet 14) is its MODIFIED
     Q:3298-3314, after Change 1's delta; the environment and immutable releases are owner tasks.
5. **CI extension points, no generators.** RP:627-629 makes a multi-forge CI one CUE model. The
   template admits extra jobs through open maps (`.config/ci/verification.cue:91`, `:98`) but closes
   triggers, permissions and every `verify` field (`:84-92`), sets no GitLab `auto_cancel`
   (`:99-103`) and runs one installed ETHOS with `--full` on every runner (`:40`, `:51`). Change 7
   turns decision 10's adopter-facing practices into template fields, keeps what the retired
   generators fixed and re-expresses Change 1's CUE; `lane project` stays the only generator
   (`src/ethos/contracts/operations/lane_repair.py:96-108`), and its `--check` is the gate:
   - the invocation, building ETHOS from its own tree where the distribution name says so
     (PDC:338-340); `default`, offline after decision 1, on every runner and `full` on the Linux
     runner, so network floors run once per push per forge with no new set or field;
   - Linux as the default runner and macOS by default only on `main` and release refs; platform ids
     apart from runner labels (Q:2921-2933); timeouts per job class;
   - concurrency per event (a newer push to a proposal, pull or merge request cancels its earlier
     run; `dev`, `main` and dispatches never), GitLab `auto_cancel` per ref and infrastructure-only
     retry (packets 14, 15, 20);
   - no persisted checkout credentials, an explicit token where an adopter is private, lock-keyed
     download caches outside release jobs, written by the `main` schedule that proposals read
     (packets 3, 16), and `actions.lock` checked offline by `lane project --check` alone, while the
     forge's Require-lockfile policy is an owner task with a readback (packet 1);
   - an admission job per forge (adapters:567-571), decision 3's base input, Mise variables as
     defaults, typed dispatch inputs through `env`, and GitLab `spec:inputs` for the batch-head
     run and in place of the offline-candidate variable (packet 10), with the product lines it
     needs, since today each forge file is rendered as one YAML document
     (`src/ethos/adapters/projections/cue.py:78-83`); `verify` leaves `v*` tag pushes (`:85`),
     whose commit `dev`'s run verified (Q:3213-3215);
   - a CUE package as the source (`cue.py:135-140` writes two files already) and a call of rc's
     pinned CI carrier on GitHub once it exists (rc:119-121; pf:68-69), with GitLab keeping the
     projected job while its component is unqualified (DR-0021:51);
   - in 0.3.0, a `beta` move reads the build's full-matrix run from the typed input or B6's
     rehearsal (DR-0022:47-50). Shape fixtures accept the template; ETHOS instantiates it with its
     journeys and builds as extension jobs, needing no field an adopter cannot declare.
6. **One release operation, inverted.** The product owns the changelog grammar
   (`src/ethos/repository/release/changelog.py`), the signed tag (`land --release`) and same-object
   publication to every peer (`ethos publish`; PDC:301-309); adopters rebuild notes, `SHA256SUMS`,
   forge releases and readback. A `release` group operation (working name `release distribute`,
   chained with rc's `release rehearsal` and `release accept` at rc:436-437 and rc:605) produces
   the published digests and the attested `SHA256SUMS`; `release accept` binds them after the
   journey (rc:601-607). It follows C4's two halves, C5, B6 and B11, which edit the same assembler:
   - Peers: RG's topology declares which peers are release channels, for ETHOS GitHub alone
     (DR-0021:51; pf:139-140). Bytes come from a local build or, for ETHOS, the hosted build after
     its attestation and before release creation (DS:721-734), never from another peer's run, and
     no job stores another forge's credential (PDC:301-303; rc:537-540).
   - Effects: per peer, a recheck of the tag OID and an absent or exact release (PDC:304-306);
     stage, upload, read back, then publish, an incomplete immutable release becoming a new
     prerelease; partial, UNKNOWN and recovery states stay distinct (PDC:306-307). One entry per
     asset fits `timeout.request_seconds` (180 s, `paradigm.toml:173-178`) against archives of 270
     to 383 MB (rc:622-623) unless a measured rate fits more; `authorize` now, `delegation` once A12
     lands (rc:274-276), and no effect without non-interactive authority (PDC:406-408).
   - The template's release job builds, attests and publishes to its own forge only; the all-peer
     step stays local, no GitLab attestation is promised (packet 13), and under DR-0022 the
     operation runs once per build at landing, never on a channel move (DR-0022:43-51).
   - Deletions: `_release_notes`, `_sha256` and the checksum part of `assemble` in
     `tools/ci/delivery/release_assets.py`, after C5 deletes its `http:ethos` writer (`:141-158`);
     the operation's readback replaces B's release readback (rc:384-386), so one remains; ETHOS's
     assembly output moves to `build/artifacts` (`src/ethos/contracts/artifacts/topology.toml`).
7. **Verb defaults and the agent entry.** The paradigm requires `bootstrap`, `check` and `fix` as
   tasks of the toolchain owner (RP:555-560). A repository's own bodies hold its own steps and stay
   its own (PDC:588; DR-0017:49-50): `repair-paradigm` writes default bodies only where none exist,
   and no bump touches them. Formation's AGENTS.md already points to `status` and `agent_guidance`
   (`src/ethos/adapters/repo/starter/formation.py:40-46`; `src/ethos/repository/context.py:91-97`),
   and a repository adds its purpose. The Skill travels with the product and is not copied
   (Skill:37-38, 48-50), so CONTRIBUTING.md gets no common sections: restated workflow becomes one
   pointer to `ethos status` or goes. The paradigm reports an agent-specific root entry file in
   every governed repository, report-only until its owner migrates. `adopt --exit` keeps today's
   effects (`src/ethos/adapters/repo/hook/exit_plan.py:1-10`), and its plan names each tracked
   projection ETHOS wrote (pin line, default bodies, pointer) for the exit Change (PDC:391-392).
8. **Reach and retirement are attested per release.** Change 6 binds, per release, one Attestation
   predicate (PDC:108) per shipped obligation: its reach (the adopters it selects), its state
   (reporting or armed), its duplicate-owner gaps and its read-back deletions, over the adopters
   that B3's source names (rc:457-472), read offline from their accepted trees. Its readers are B3's
   rendering of the curated entry (pf:121-122) and TP's pending delivery items. PDC:347-357: no
   existing predicate records it; without it the owner's request for a systematic guarantee (AR:22)
   is unprovable per release; its owner is the `distribution` specification, and it lives as long
   as the release's Attestations. AR's blocks, escapes, dead rows and cost (AR:1889-1894) stay
   pending: they need adopter proof events, which ETHOS cannot read offline without the reporting
   channel that the Non-Goals exclude. No `status` figure, line count or aggregate remains
   (DR-0010:66-69); CI figures stay an on-demand read with the caller's forge authority, read by
   Change 1's delivery item, and lag stays with B3 and B14 (pf:87-88).
9. **Budgets: one rule.** Product: 85,000 line-equivalents since `f60574afb`
   (`.config/checks/format-selection/policy.toml:7`), 80,126 measured (archived
   `product-budget-step-85/tasks.md:7-9`), with one product change since, `514136415` (+11/-9), so
   about 4,874 left; rc's sized claims (+3,210; rc:84-87, 115-123, 140-152) pass DR-0025's 83,000
   review (DR-0025:59-60), which 97f828 runs inside the RC. Tests: 101,764 of 105,000 at
   `f420780e8` (archived `history-rebuild-map/tasks.md:18-19`) plus 402 unmeasured raw lines; rc's
   sized claims (about +3,880) with Changes 1, 2 and 10 (+130) overrun by about 774, or 1,176 with
   those lines, and DR-0023's 103,000 revisit (DR-0023:67-68) falls inside the RC. Tools: 8,378 of
   10,000 (`test-budget-step/tasks.md:9`) against rc's sized +1,615 (rc:172-178), 7 to spare:
   - The RC densifies across its queued Changes first (rc:175-177); if the measured need remains,
     one standalone 5,000 test step, a DR-0023 successor owned by 97f828, lands before the first RC
     Change whose readiness would pass 105,000 (DR-0023:52-53; DR-0010:52-58).
   - Changes 1 and 10 net zero tools, and Changes 1, 2 and 10 count with the RC.
   - No product duplication is named today, so one DR-0010 necessity review runs at Change 3's
     readiness, with the adopter deletions that Changes 3 to 5 enable as evidence, unless rc's
     reductions (rc:402-403) land first; TP states which applies, and Changes 3 to 9 and 11 to 13
     wait for it. The 0.3.0 Changes pay their tests from the room the RC step leaves, or by
     removals; otherwise that review covers tests as well as product.
   - Caps, product/tests/tools, measured at readiness (inference): 1: 0/+60/0; 2: rc's sizes plus
     +20/+40/0; 3: +450/+150/-400; 4: +550/+250/-380; 5: +300/+150/-300; 6: +150/+120/0; 7:
     +180/+220/0; 8: +600/+450/-100; 9: +120/+100/0; 10: 0/+30/0; 11 to 13: +20/+40/0 each; each
     splits every function above 15 that it moves or extends (`test_decision_density.py:13`).
10. **Hosted CI proves what the local proof cannot, once per plane.** Hosted CI is a later
    observation that gates no landing (`gate-runner.md:43-44`; PDC:498-502). Change 1 applies this
    to ETHOS's pipeline at zero product lines:
    - Roles by event: a ref that ETHOS publishes to both peers gets the full set once on GitHub and
      admission plus conformance on GitLab; merge-request pipelines and a GitLab `main` whose tree
      differs from `dev` keep the full set on GitLab, which treats every merge request as
      GitLab-only (inference). MODIFIED Q:3211-3248 and Q:722-727; rc's A9 item 8 (rc:371-372) and
      A11 (rc:310-311) read admission plus conformance from GitLab.
    - Admission: GitHub's range admission moves from `quality` (`pipeline.cue:370-377`) into
      `commit-policy`, run for every push and pull-request event (`:315`), so each forge admits one
      range per event (Q:3213-3217; adapters:567-571).
    - Tiers: a push runs Linux x64 conformance at 3.12 and 3.14, 3.13 until B4's suites land
      (rc:444-446), and one macOS arm64 leg at 3.12. The full matrix runs on each D19 batch's
      candidate head before its tag: on GitHub by a typed dispatch input (`qualify_head`, then B6's
      `rehearse_head`), on GitLab by a `web` or `api` pipeline-source rule on the release lane's
      proposal ref whose commit must match the declared head. The guide requires both before
      `land --release`, a prose gate until B7 enforces GitHub's half (rc:436-440). Drift schedules
      stay drift only, and the lane owner's typed input runs the Windows legs.
    - Speed: no supply image on GitHub; lock-keyed download caches (Mise downloads verified by
      checksum, uv with `uv cache prune --ci`; packet 16), written by the `main` schedule that
      proposals read, never in release jobs.
    - Checks: one aggregate with a stable name (`hosted checks`; a hosted result is no repository
      proof, Q:619-620) needs every per-push job, `commit-policy` included, and replaces the two
      placeholders (`pipeline.cue:429-450`); matrices key on platform ids (MODIFIED Q:2921-2933).
    - Safety: `actions.lock` (packet 1); no persisted checkout credentials; permissions widen only
      in release jobs and `supply-image` (`:276-279`); a timeout per job class from measured p99,
      above its gates' own; protected refs' GitLab jobs on protected runner tags
      (`verification.cue:26-29`); a newer push to a pull or merge request cancels its earlier run
      (packets 14, 15; MODIFIED Q:3298-3314).
    - Measure: from a run's first attempt to its final conclusion, with n, a capacity cancellation
      a failure and the baseline re-measured so; targets of about 40 minutes on GitHub and under 15
      on GitLab carry 10 percent tolerance, kept by Change 1's lane owner, later the template's.
11. **Host admission is a declared class.** The contract that rc's `host-reservation` implements
    (rc:97-101): work launched as yielding, such as a render, holds no host slot (one by default,
    `src/ethos/adapters/gates/host_admission.py:1-12`, `:54`), and admission counts its CPU as
    available, read from its own process tree. macOS uses that class alone, since its per-state
    counters carry no nice time; Linux may add `/proc/stat`'s nice column; otherwise today's rule
    holds, two consecutive 1-minute load samples 15 s apart
    (`src/ethos/adapters/gates/proof_slot.py:52`, `:182-191`; Q:3443), and its docstring (`:5-9`)
    is corrected. MODIFIED Q:3426-3461. Acceptance on the macOS reference host: a CPU-bound nice-15
    render launched as yielding does not hold a full proof out, and the same load undeclared does.
12. **Order.** Prerequisites mean landed; Changes on one authority owner are serial (TP:375-378):
    Change 1 first among rc's `pipeline.cue` editors, Changes 4 and 5 after 3, Change 6 after B3,
    Change 9 after pf's formation Changes, and Change 10 before B5, as both edit
    `local-install-smoke` (rc:449-451). A Change closes on (a) its source acceptance: capability,
    regressions, Goal 1's shape fixtures, ETHOS's moves and a recorded read-only preview; its (b)
    delivery items wait in TP until product reports show them, or the adopter's archived Change for
    a copy no report sees (TP:31-33). First, outside any ETHOS Change, adopters retire copies of
    shipped gates and operations, hooks and lanes included, previewed with `prove`; the deferred
    families take the paradigm's branch roles (`paradigm.toml:35-38`) at their migrations.
    1. **`ci-economy`** (RC; RP:627 with Q): decision 10. (a) Projection tests; Windows and the
       emulated leg off the push path; one admission per event. (b) Ten dev-push medians within
       target, capacity per runner class, the ruleset switched and read back, schedules read back.
    2. **rc's C1, C2, C3, `release-identity`, `release-acceptance` and `adopter-bump`** (RC;
       `distribution`): decision 4. (a) rc's done conditions (rc:577-607), C1's forge check, the
       rollback preflight and the one-Change regression. (b) R; the bump to R+1; the eleven pins.
    3. **`shared-security-floor`** (0.3.0; RG:5166, MODIFIED): decision 1's rule, field, lifecycle,
       repairs and ownership gaps; `secrets` and `dependency-vulnerabilities` ship, reversing
       `secret-scan-supply`'s unarmed report. (a) Equal- and unequal-set regressions;
       `dependency_audit.py` moved. (b) No duplicate-owner gap for history scans (two Python
       services), Gitleaks wiring (the Go CLI) or scanners (the deferred families).
    4. **`shared-language-floor`** (0.3.0; Q, after 3): language gates and decision 3, with a
       MODIFIED Q:98-118 that classifies types, import boundaries, dependency hygiene, docstrings,
       module layout, tests and coverage, duplication ratio, complexity, and mutation and
       changed-line coverage by DR-0017's test, each shared with the repository's own tool and
       threshold or ETHOS-domain with its reason. (a) ETHOS's code gates and `module-layout` on the
       shipped gates; two hygiene tools moved. (b) No provider gap for twelve language
       redeclarations in six adopters, and no duplicate-owner gap for lint, type or layout copies.
    5. **`governance-floor`** (0.3.0; Q and RG, after 3, amending Q:10-16 and RG:893-897):
       decision 2's governance gates, actionlint and ShellCheck supply, `asset-validation` without
       Pillow (a development dependency, `pyproject.toml:49`), and two latent-gap reports: an ETHOS
       invocation from a source path, and a tracked hook tree beside the installed hook. (a) ETHOS's
       registry holds only its domain gates. (b) No provider gap for a deferred family's shipped-id
       copies, and no workflow-check duplicate, source-path or hook-tree report.
    6. **`obligation-reach`** (0.3.0; `distribution`): decision 8, after B3 and decision 9's
       review. (a) The predicate and its two readers. (b) The first release's predicate read back.
    7. **`ci-extension-points`** (0.3.0; RP:627): decision 5, after 1, 5 and every rc `pipeline.cue`
       editor. (a) Shape fixtures; ETHOS on the template; `spec:inputs`; a per-adopter practice diff
       without a regression. (b) No CI-generator report in the six adopters, the deferred families'
       emulators retiring with their migrations; Mise-version edits per adopter per release counted.
    8. **`release-operation`** (0.3.0; DS, with RG for topology): decision 6, after C4's halves, C5,
       B6, B11, Change 7 and DR-0022's implementing Change (DR-0022:77-79). (a) ETHOS's release runs
       it. (b) The Go CLI's and a Python service's release code retired; npm builds stay.
    9. **`shipped-verbs`** (0.3.0; RP:555): decision 7, after 4 and 8. (a) Default bodies, the
       root-entry report and the exit plan. (b) Each adopter's AGENTS.md becomes formation's pointer
       plus its purpose, by shape, and restated workflow becomes pointers as owners classify it.
    10. **`installed-hook-smoke`** (RC; Q): a step of `local-install-smoke` that runs the generated
        `pre-commit` under the installed runtime on the candidate, the whole hook beyond
        `514136415`'s unit test. (a) A fixture the installed hook would refuse is refused. (b) None.
    11. **`arm-security-floor`** (0.3.0): names the release from which Change 3's gaps block, one
        release after they report, never for a lockfile class without an auditor. (a) Its
        regression. (b) The first armed release read back.
    12. **`arm-language-floor`** (0.3.0): the same for Change 4.
    13. **`arm-governance-floor`** (0.3.0): the same for Change 5, its two reports included.
13. **Prior designs and owner requests.** Each item gets one disposition (PDC:536-543); AR's author
    and a225 are told, and the owner sees AR's supersessions at approval. Accepted: AR's lifecycle
    (AR:1879-1888) through RG:5989-5993 and Changes 11 to 13; its duplicate-tool refusal
    (AR:1826-1830) as Change 3's gaps; its membership predicate (AR:1251-1258) as the Base rule;
    its conformance cases as shape fixtures; "nothing is generated" (AR:780-781) in decision 7; of
    its outcome record (AR:1889-1894), reach and retirement in decision 8, with blocks, escapes,
    dead rows and cost pending. Of its principle rows (AR:1853-1866), duplication ratio, complexity,
    and mutation and changed-line coverage are classified in Change 4, the pure core is
    ETHOS-domain (the product's architecture), and an adopter's own supply currency is pending, as
    PDC:433-442 scopes currency to the product's supply (owner 97f828, review at Change 2's
    readiness). Rejected under PDC:347-357: `gate-rows` (AR:1454), packs and presets as entities
    (AR:757-765, 1465), the contract integer and the declared-core slot (AR:1259-1263). Pending
    until an adopter carries one (DR-0012:85): TypeScript beyond the JavaScript floor, Rust, C, C++
    (AR:1471). Superseded: `budget-ratchet` (AR:1435) by decision 9, `platform-matrix` (AR:1450) by
    Change 1's tiers. The owner's 10-31 request (AR:9-10) is met by the fourteen families and the
    11-01 requests (AR:21-22) partly, the pending items remaining. The 10-31 route maps to decisions
    1 to 5 and Changes 3 to 7, without its vocabulary steps; its files stay with a225 until archive.
    The owner approved these dispositions on 2026-11-13 ("同意 4 项建议"), with three settings: the
    Python service's R9 exception is pre-approved with Change 7 as its exit; a solo release
    environment takes the `v*` pattern, no admin bypass and immutable releases, reviewers waiting
    for a second maintainer; the documentation repository's Windows runner stays through 0.2.0.

## Risks / Trade-offs

- **Breakage.** Floors report a release before arming, yet an advisory can fail an unchanged tree
  until accepted, and formation's first landing is judged by its candidate alone.
- **Concentration, budgets and order.** A shared floor's defect blocks every adopter at once,
  bounded by D19's fix-beta exception (rc:156-158); the 0.3.0 Changes wait on a review whose outcome
  is open; Change 1 sits on R's critical path.
- **Planes and runners.** On published refs GitLab's green means admission and conformance, and its
  batch-head half stays a prose gate after B7, which reads GitHub only (rc:436-440). ETHOS's GitLab
  jobs share one runner tag (`pipeline.cue:645`) and pull over flaky egress (`:639-643`), isolation
  and a mirror staying with the CI guests' owner; a documentation repository's Windows ARM64 runner
  runs an ETHOS Windows runtime that only batch heads qualify.

## Open Questions

- Does C1's forge check find a digest mismatch among beta.7 to beta.10? Is the host store's
  consumer record B3's adopter source (rc:541-542)? Does uv's audit leave preview before Change 3?
- Are versions across workspace packages shared, and should the paradigm check decision records?
