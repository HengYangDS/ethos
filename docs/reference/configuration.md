---
subject: docs:reference:configuration
role: reference
state: canonical
relations:
  current_owner: ../../openspec/specs/repository-paradigm/spec.md
---

# Configuration Plane

Status: canonical.

Purpose: map each ETHOS configuration file under `.config/` to the tool or repository check that consumes it.

See also: [Reference Documentation](README.md), the [repository-paradigm specification](../../openspec/specs/repository-paradigm/spec.md), whose "Tool configuration lives in the configuration plane" owns this plane, and [DR-0012: Repository Paradigm](../decisions/dr-0012-repository-paradigm.md).

`.config/` holds only configuration that a tool or repository check consumes, grouped by that consumer. It is a
configuration plane, not a truth center.

## Separation of concerns

- `pyproject.toml` owns Python package/workspace metadata and uv wiring. Its
  remaining native tool tables are not permission to duplicate policy owned
  by an explicit configuration file.
- `.config/checks/pytest/pytest.toml` is the pytest config owner and points pytest runtime cache to `build/runtime/tool-cache/pytest`, not `.config/`. Owner scripts pass it with `-c` and `--rootdir=.`. Native `pythonpath` entries are relative to the configuration directory and explicitly resolve to the repository and its `src/`; `--rootdir` does not rebase those entries.
- [The Ruff policy](../../.config/checks/ruff/ruff.toml) owns lint and formatting rules. Native
  CLI and hook consumers select this exact nested policy; no root pointer remains.
  CLI caches are bound explicitly to `build/runtime/tool-cache/ruff/`.
  The package runtime supplies Ruff for selected staged Python checks. These
  checks consume index bytes through native stdin, not uncommitted worktree
  contents. Missing bound supply is a failure, not an implicit skipped check.
  Editor integration remains a separate acceptance boundary.
- `.config/checks/<owner>/` and `.config/release/<owner>/` are named by the consuming tool, keeping its
  native file name, or by the repository check whose parameters live in `policy.toml`.
- [Native format selection](../../.config/checks/format-selection/policy.toml) has one product owner,
  `ethos.repository.policy.quality.format_selection`. The `format_selection` Nox session runs
  `tools/ci/format_selection.py`; `ethos lane format` and the shared configuration provider use
  the same assignments. Native generators, locked upstream members and package-manager outputs
  retain their exact byte owners.
- Root `noxfile.py` is the native discovery entry for `tools/ci/sessions.py`,
  which owns the executable Python lint proof surface inside the
  single uv-locked `.venv`: unsuppressed Ruff check and Ruff format check,
  both bound to `.config/checks/ruff/ruff.toml`. Nox creates no second
  environment, and Ruff caches remain under `build/runtime/tool-cache/ruff/`.
  Root `pyproject.toml` remains free of Ruff policy.
- `.config/checks/coverage/coverage.toml` owns Python line-and-branch measurement; `.config/checks/coverage/policy.toml` owns the required hard floor. Default proof, full proof, and local CI enforce that same floor against current-HEAD evidence. Generated coverage data and XML go to `build/evidence/quality/tests/coverage/`, pytest JUnit evidence goes to `build/evidence/quality/tests/pytest/`, pytest cache goes to ignored `build/runtime/tool-cache/pytest/`, and pytest temporary directories default outside the repository so fixture roots cannot masquerade as repository truth. Pytest policy stays in `.config/checks/pytest/pytest.toml`, which every invocation passes with `-c`; a bare `pytest` at the root applies no project policy.
- `.config/checks/docstrings/policy.toml` owns public-surface docstring coverage.
- `.config/checks/module-layout/policy.toml` owns all tracked Python as the
  repository-wide semantic scope, plus the narrower product-package topology
  scope, ambiguous naming, facade, command-owner, and import-boundary policy.
  `uv run --frozen --offline python -m nox -s module_layout` is the reusable runner.
- `.config/checks/taplo/taplo.toml` owns TOML canonical formatting. Original
  locked Prettier owns authored JSON and YAML formatting through
  `.config/checks/prettier/prettier.toml`; JSON parsing and the native semantic
  yamllint rules retain syntax, duplicate-key and alias obligations without a
  second layout policy. The installed `config-quality` provider and native
  `config_quality` Nox projection check the same exact authored inputs. Native
  format fixing uses the commands declared in `.config/checks/format-selection/policy.toml`.
  Dependency resolution members keep their existing package-manager byte owner
  from that declaration; official OpenSpec, projections and explicitly bound
  source contracts retain their separate verification. The replaced stdlib JSON
  formatter and its configuration are retired, not retained as another authority.
  Shipped policy remains mandatory, native increments cannot hide its failures,
  and refusal preserves bytes. No adopter controller or source environment is
  required by the installed provider.
- `.config/checks/yamllint/.yamllint.yaml` owns native YAML semantic lint, including CI,
  hook and quality configurations. OpenSpec YAML remains under the pinned
  official validator. CI invokes both owners through their existing gates.
- [The Gitleaks policy](../../.config/checks/gitleaks/gitleaks.toml) owns custom rules and
  extension of native defaults. Hook and CI select it explicitly. Mise owns
  its locked supply; `tools/ci/toolchain/native.py` verifies the installed bytes.
  The `secrets` Nox session scans an isolated `git ls-files` mirror,
  preserving tracked-source coverage without scanning ignored host state.
- `.config/checks/shellcheck/.shellcheckrc` owns ShellCheck policy; the `shell_lint` Nox session resolves the locked cross-platform `shellcheck-py` executable.
- `.config/checks/prettier/prettier.toml` owns Markdown spacing, container layout
  and formatting style; `.config/checks/markdownlint-cli2/.markdownlint-cli2.yaml` owns
  non-formatting document and link semantics, plus the spacing and style rules of
  official OpenSpec Markdown, which has no formatter. The `markdown_lint` Nox session
  projects the shared product gate and its shipped, lock-bound native tools.
  Both checks consume the same current authored files. Immutable records are
  retained without rewrite; generated and local outputs are not source inputs.
  The shared gate passes exact named documents and the explicit policy to the
  unchanged official Markdownlint API with globs, imports, inline configuration
  and fixing disabled, so local configuration cannot drop inputs, suppress rules
  or write source.
- `.config/checks/codespell/codespell.toml` supplies the mandatory native spelling
  policy in both wheel and source distributions. The shared `prose` Gate and
  source Nox projection use one installed owner over exact authored copies,
  rejecting source writes and ambient policy; local policy only adds checks.
  Codespell does not replace repository-owned Vale styles or terminology rules.
- `.config/checks/deptry/policy.toml` owns dependency hygiene policy. The
  `dependencies` Nox session invokes `tools/ci/dependency_hygiene.py` for the
  sole Python distribution and its locked supply. The runner passes the declared
  first-party names, module mapping and per-rule exceptions to native Deptry;
  root `pyproject.toml` remains the dependency manifest, not a second policy.
- `.config/checks/dependency-vulnerabilities/policy.toml` owns the native dependency audit boundary. The `vulnerabilities` Nox session calls `tools/ci/dependency_audit.py` to audit Python and npm locks, retaining bounded native observations and one input-bound verdict. A finding that no official stable release fixes is reported without blocking: every locked npm artifact that ships it is already its registry latest release, or a Python advisory names no newer stable fix version. Fixable or unobserved findings still block. Online security guards package delivery without making offline tests depend on advisory availability; hosted CI and publication remain separate claims. Landing re-evaluates a captured audit's raw findings and requires the product policy it was captured under: the policy the selected product ships, or, for ETHOS's own source, whose committed file is the product policy, that file at the exact head.
- [The secret-scanning policy](../../.config/checks/gitleaks/gitleaks.toml) is passed explicitly to every scan, including staged pre-commit admission; `.config/mise/config.toml` and `.config/mise/mise.lock` own native tool selections and platform artifact digests. The `secrets` Nox session obtains verified project-local supply through `tools/ci/toolchain/native.py`, scans a mirror of the tracked files and passes the policy explicitly. Hosted proof uses the same supply owner; neither path installs system files or trusts ambient scanner bytes.
- `tools/ci/repository_hygiene.py`, invoked through the `repository_hygiene` Nox session, owns cross-file hygiene such as tracked-file size, LF endings, final newline, JSON parseability, merge-conflict markers, and the zero-suppression invariant.
- `.config/mise/config.toml` and `.config/mise/mise.lock` select native developer/CI supply through native discovery. The existing
  bootstrap stages the bound release's official mise executable for the host
  platform, accepted only with its digest from the bootstrap record in
  `.config/checks/ci-projection/policy.toml`.
  Installation is staged and bounded; observation does not install tools.
  Isolated consumers preserve this same nested layout; disposable copies do
  not own versions or checksums.
- `.config/ci/pipeline.cue` composes both provider projections from native gate
  and runtime inputs. `.github/workflows/ci.yml` and `.gitlab-ci.yml` are
  generated, not editable sources. The `ci_templates` Nox gate verifies
  native compilation, exact output bytes and input bindings.
  `uv run --frozen --offline python tools/ci/ci_templates.py check-templates --render`
  emits both outputs once without writing tracked files.
- `.config/checks/ci-projection/policy.toml` declares provider emulator selection,
  events, jobs, images and time limits. `tools/ci/ci_projection.py` consumes
  that declaration; emulator output is local evidence, not hosted CI status.
  Its `[[forge_surface]]` entries declare the issue and change forms each Forge projects and
  their required sections; `tools/ci/ci_projection.py` checks them. CUE compiler inputs keep
  their native carriers: a string reference stays TOML, and a typed reference names an exact
  `path` and `format`:

  ```toml
  [compiler.inputs]
  policy = "policy.toml"
  package = { path = "package.json", format = "json" }
  ```

- `python -m tools.ci.ci_projection` validates GitHub workflows through locked
  Actionlint and finite-input ShellCheck, without a shell launcher. Native policy
  and supply remain under `.config/mise/config.toml`, `.config/mise/mise.lock`
  and the bound Python environment; missing supply fails without PATH fallback.
- `.config/checks/lychee/lychee.toml` owns link-check behavior. Its supply
  declaration maps the executable to the official `lychee-bin` wheel; the
  production dependency and `uv.lock` own version and artifact identity. The
  gate resolves the executable beside its bound Python, without ambient PATH.
- `.config/checks/hosted-observation/policy.toml` owns hosted provider observation envelopes; the `hosted_observation` Nox session records GitHub/GitLab provider facts or tool-discovery state without claiming repository proof, hosted CI success, or remote publication.
- `.config/checks/format-selection/policy.toml` owns fail-closed executable-carrier
  admission and file-format boundary checks; `uv run --frozen --offline python -m nox -s format_selection`
  is the reusable runner.
- `.config/checks/architecture-projection/policy.toml` owns architecture projection
  drift checks from the `docs/architecture/models/` source to generated Mermaid. The generated
  diagram is review aid, not architecture truth.
- `src/ethos/contracts/artifacts/topology.toml` owns generated-state location
  and lifecycle rules, interpreted by its adjacent product module. No parallel
  local-state configuration is maintained under this directory.
- `.config/release/release-sbom/policy.toml` selects the built-wheel subject, SPDX
  output and claim boundary. Mise owns the Syft version and artifact checksums.
  SBOM generation does not establish publication, signing or SLSA conformance.
- `.config/checks/import-linter/import-linter.toml` owns the import-layer contracts of the
  one `ethos` package; the `import_boundaries` Nox session and the `import-boundaries` gate
  check them.
- `.config/checks/ty/ty.toml` owns Python type-check selection and rules for the
  `python-types` gate.
- `.config/checks/vale/vale.ini` and its `styles/` vocabularies own prose style for the
  `prose` gate, beside Codespell.
- `.config/checks/lychee/policy.toml` declares the locked Lychee supply that the link
  check in `lychee.toml` runs on.
- `.config/checks/repository-hygiene/policy.toml` holds the repo-shape knobs that
  `tools/ci/repository_hygiene.py` executes.
- `.config/ci/verification.cue` is the shared `#Verification` CI model that
  `.config/ci/pipeline.cue` instantiates for both providers.
- `.config/ci/runners.toml` declares the executables each forge's runner provides
  beyond the repository toolchain and the product runtime.
- `.config/ci/supply/Dockerfile` and its `.dockerignore` build the locked Linux ARM64
  supply image for GitLab jobs; source and policy stay in the CI checkout.
- `.config/ci/pipeline.cue` models every hosted job. Its one bootstrap command
  list runs native uv commands and `tools/ci/toolchain` modules; hosted CI YAML
  is only the provider projection of that model. `.config/mise/config.toml`
  declares the `bootstrap`, `check` and `fix` verbs for local use.
- `system/gates.toml` owns each gate's identity, profile, executable boundary,
  evidence class, and proof-floor membership. Native configuration and supply
  files remain the unique owners of tool-specific policy and versions.

## Root discovery and remaining migration boundaries

Placement follows the actual consumer, not a blanket root-file exemption.

- Python and npm manifests remain beside their ecosystem lockfiles at the
  workspace boundary. Native Git metadata and attributes retain their Git scope.
- Ruff consumers pass `--config .config/checks/ruff/ruff.toml` explicitly.
- `noxfile.py` is a small native entrypoint, not another session implementation.
- `.gitlab-ci.yml` is a generated provider entrypoint. Its meaning comes from
  the CUE source and native inputs, not separately authored YAML.
- Gitleaks consumers pass `--config .config/checks/gitleaks/gitleaks.toml`
  explicitly; missing or malformed policy is an execution failure.
- [The optional pre-commit configuration](../../.config/checks/pre-commit/.pre-commit-config.yaml) invokes
  existing Nox checks. Run it with an explicit `--config` path; no root copy
  is retained. Do not install it over the ETHOS-owned Git hook.
- README, contribution guidance, license and changelog are reader entrypoints
  or project records, not tool-policy configuration.

Mise uses native nested discovery through [its configuration](../../.config/mise/config.toml)
and [lockfile](../../.config/mise/mise.lock) under `.config/mise/`. Root copies are not retained.

## Optional pre-commit checks

The optional framework is a developer convenience, not the full proof or the
installed Git hook. Its commands call existing Nox owners rather than defining
another quality policy. From the repository root:

```bash
uv run --frozen --offline pre-commit run --config .config/checks/pre-commit/.pre-commit-config.yaml --all-files
```

The source-bound `config_quality` Nox session validates this same native YAML.
Git hook installation remains owned by `ethos hook install`.

## Repository surfaces

Each repository surface holds one kind of fact; the owner column names the carrier that defines it.

| Surface                   | Holds                                                                                                              | Does not hold                                                                           | Owner                                                                                                                                                             |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.ethos/`                 | The tracked ETHOS binding: profile, workspace, release and rules                                                   | Change intent, tool-native configuration, domain truth, durable evidence, mutable state | repository-paradigm "The binding uses only ETHOS-defined files"                                                                                                   |
| `<git-common-dir>/ethos/` | Repository-local coordination shared by worktrees: Leases, bounded requests, operation receipts, transaction state | Durable Attestation selection, product meaning, portable configuration                  | kernel "Durable event-like values are consumed Attestations" (scenario "Git-common state stays outside checkouts"); [Local State](../architecture/local-state.md) |
| `.config/`                | Configuration that a tool or repository check consumes, grouped by that consumer                                   | Scripts, tool implementation, documentation, evidence, user decisions                   | repository-paradigm "Tool configuration lives in the configuration plane" and "The configuration plane holds only consumed configuration"                         |
| `rules/`                  | Executable duties, each with the command, artifact or verifier its Evidence names                                  | Tool implementation details, generated state                                            | [Rules System](../../rules/README.md)                                                                                                                             |
| `docs/`                   | Explanation, reference, how-to, decisions, research and history, each linking its owner                            | Normative policy outside the PDC and its linked owners, mutable state, evidence         | [Docs Registry](../governance/docs-registry.md#semantic-authority-and-carrier-boundaries)                                                                         |
| `system/`                 | Machine-readable product contracts, in the product repository only                                                 | Adopter domain truth; an adopter needs no `system/` tree                                | [System Contracts](../../system/README.md)                                                                                                                        |
| `openspec/`               | Official OpenSpec Changes, accepted specs and their native lifecycle                                               | Execution authority, runtime state, proof by itself                                     | repository-governance "Official OpenSpec Governance"                                                                                                              |
| `.agents/`                | Repository-local Skills and their activation routes                                                                | An independent truth store                                                              | [Skill Rules](../../rules/skills.md)                                                                                                                              |

## `.ethos/` bindings

The binding layer holds only ETHOS-defined files (repository-paradigm "The binding uses only ETHOS-defined files"):

- `.ethos/profile.toml`: the repository profile. The profile model (`src/ethos/repository/profile.py`) owns its fields, and repository-governance "Repository profile is a strict current binding" owns its validation.
- `.ethos/release.toml`: `[protected_refs]`, `[host_profile]`, `[publication]` with its local verification and installation commands, `[[publication.peers]]` (identity, provider, role, Git remote, capabilities, Forge repository and CI surface), `[attestation]` and `[release]`. `src/ethos/repository/release/publication.py` owns the peer fields, and repository-governance "Declared publication peer topology" owns the topology.
- `.ethos/rules.toml`: the active rule profiles and repository rules (`src/ethos/repository/policy/rules/config.py`).
- `.ethos/workspace.toml`, when present: the workspace binding.

## Boundary rule

Do not duplicate the same policy in multiple files. If a provider surface needs a
policy, make it invoke the owning config or script instead of re-stating the
policy inline.

## Generated/local state topology

Configuration under `.config/checks/` owns policy only. Runtime caches and
local generated outputs must use semantic ignored homes: `<git-common-dir>/ethos/`,
outside every checkout, for host-local coordination, `build/runtime/tool-cache/<tool>/` for tool caches,
the project `.venv/` for the one uv-locked Python environment,
`build/runtime/work/<provider>/` for provider emulator work state,
`build/evidence/` for machine evidence, `build/ethos/` for ETHOS machine
projections, and `build/artifacts/<kind>/` for local package/build outputs.
Root cache directories such as `.import_linter_cache/`, `.pytest_cache/`,
`.ruff_cache/`, `.uv-cache/`, and root `dist/` are denied residue, not owners.
