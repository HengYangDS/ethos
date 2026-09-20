# Configuration Layout

`.config/` holds tool-native configuration and hosted-runner setup. It is a
configuration plane, not a truth center.

## Separation of concerns

- `pyproject.toml` owns Python package/workspace metadata and uv wiring. Its
  remaining native tool tables are not permission to duplicate policy owned
  by an explicit configuration file.
- `.config/checks/pytest/pytest.toml` is the pytest config owner and points pytest runtime cache to `build/runtime/tool-cache/pytest`, not `.config/`. Owner scripts pass it with `-c` and `--rootdir=.`. Native `pythonpath` entries are relative to the configuration directory and explicitly resolve to the repository and its `src/`; `--rootdir` does not rebase those entries.
- [The Ruff policy](checks/ruff/ruff.toml) owns lint and formatting rules. Root
  `ruff.toml` contains only native inheritance and the repository-relative cache
  binding; configured CLI, hook and editor consumers retain that discovery entry.
  Native discovery parity does not prove editor integration or installed-hook
  enforcement; the latter still needs its missing-tool behavior repaired.
- `.config/checks/<concern>/` holds reusable tool payloads by concern.
- Root `noxfile.py` is the native discovery entry for `tools/ci/sessions.py`,
  which owns the executable Python lint proof surface inside the
  single uv-locked `.venv`: unsuppressed Ruff check and Ruff format check,
  both bound to root `ruff.toml`. Nox creates no second
  environment, and Ruff caches remain under `build/runtime/tool-cache/ruff/`.
  Root `pyproject.toml` remains free of Ruff policy.
- `.config/checks/coverage/coverage.toml` owns Python line-and-branch measurement; `.config/checks/coverage/policy.toml` owns the required hard floor. Default proof, full proof, and local CI enforce that same floor against current-HEAD evidence. Generated coverage data and XML go to `build/evidence/quality/tests/coverage/`, pytest JUnit evidence goes to `build/evidence/quality/tests/pytest/`, pytest cache goes to ignored `build/runtime/tool-cache/pytest/`, and pytest temporary directories default outside the repository so fixture roots cannot masquerade as repository truth. Pytest policy stays in `.config/checks/pytest/pytest.toml`; root `pyproject.toml` carries only the pytest discovery cache routing invariant for bare pytest and IDE invocation.
- `.config/checks/docstrings/policy.toml` owns public-surface docstring coverage.
- `.config/checks/module-layout/policy.toml` owns all tracked Python as the
  repository-wide semantic scope, plus the narrower product-package topology
  scope, ambiguous naming, facade, command-owner, and import-boundary policy.
  `uv run --frozen --offline python -m nox -s module_layout` is the reusable runner.
- `.config/checks/taplo/taplo.toml` owns TOML canonical formatting. `.config/checks/json/format.toml` owns path-selected Python stdlib JSON formatting: ordinary JSON is two-space pretty form, while schemas and evidence remain compact machine carriers. The `config_quality` Nox session invokes the exact locked owners without shell, PATH, or dynamic dependency fallback.
- `.config/checks/yaml/yamllint.yaml` owns ETHOS-authored YAML linting,
  including CI, hook, and quality configurations. OpenSpec YAML remains under
  the pinned OpenSpec validator. CI invokes both owners through their existing
  lifecycle gates.
- `.config/checks/shell/.shellcheckrc` owns ShellCheck policy; the `shell_lint` Nox session resolves the locked cross-platform `shellcheck-py` executable.
- `.config/checks/markdown/.markdownlint-cli2.yaml` owns Markdown lint policy;
  the `markdown_lint` Nox session executes the exact `package-lock.json`
  dependency without ambient installation. The lint-only gate covers declared
  maintained Markdown, including official OpenSpec artifacts under the native
  artifact-specific rules. Historical evidence paths grant no format exemption;
  generated and local outputs remain outside the declared source globs.
- `.config/checks/prose/codespell.toml` owns report-first prose spelling policy;
  the `prose` Nox session runs locked `codespell` without rewriting files.
- `.config/checks/deptry/policy.toml` owns dependency hygiene policy. The
  `dependencies` Nox session invokes `tools/ci/dependency_hygiene.py` for the
  sole Python distribution and its locked supply. The runner passes the declared
  first-party names, module mapping and per-rule exceptions to native Deptry;
  root `pyproject.toml` remains the dependency manifest, not a second policy.
- `.config/checks/schema/jsonschema.toml` owns JSON Schema metaschema hygiene; `uv run --frozen --offline python -m nox -s schemas` validates tracked schema documents while command payload validation stays in ETHOS command tests and runtime checks.
- `.config/checks/security/audit.toml` owns the native dependency audit boundary. The `vulnerabilities` Nox session calls `tools/ci/dependency_audit.py` to audit Python and npm locks, retaining bounded native observations and one input-bound verdict. Online security guards package delivery without making offline tests depend on advisory availability; hosted CI and publication remain separate claims.
- [The secret-scanning policy](checks/secrets/gitleaks.toml) is reached through the root Gitleaks discovery reference; `.config/mise/config.toml` and `.config/mise/mise.lock` own native tool selections and platform artifact digests. `tools/ci/scripts/run-secrets-scan.sh` obtains verified project-local supply through `tools/ci/toolchain/native.py` and passes the policy explicitly. Hosted proof uses the same supply owner; neither path installs system files or trusts ambient scanner bytes.
- `tools/ci/repository_hygiene.py`, invoked through the `repository_hygiene` Nox session, owns cross-file hygiene such as tracked-file size, LF endings, final newline, JSON parseability, merge-conflict markers, and the zero-suppression invariant.
- `.config/mise/config.toml` and `.config/mise/mise.lock` select native developer/CI supply through native discovery. The existing
  Python bootstrap prepares missing mise with .config/ci/mise-install.sh,
  a version-bound official generator projection checked by ci_templates.
  Installation is staged and bounded; observation does not install tools.
  Isolated consumers preserve this same nested layout; disposable copies do
  not own versions or checksums.
- `.config/ci/pipeline.cue` composes both provider projections from native gate
  and runtime inputs. `.github/workflows/ci.yml` and `.gitlab-ci.yml` are
  generated, not editable sources. The `ci_templates` Nox gate verifies
  native compilation, exact output bytes and input bindings.
  `uv run --frozen --offline python tools/ci/ci_templates.py check-templates --render`
  emits both outputs once without writing tracked files.
- `.config/checks/ci/templates.toml` declares provider emulator selection,
  events, jobs, images and time limits. `tools/ci/ci_projection.py` consumes
  that declaration; emulator output is local evidence, not hosted CI status.
- `.config/checks/github/actionlint.toml` owns GitHub workflow syntax policy;
  `tools/ci/scripts/run-actionlint.sh` executes the provider syntax gate and
  resolves the exact installed tool through `.config/mise/config.toml` and `.config/mise/mise.lock`; missing
  supply is an explicit failure, never an ambient PATH fallback.
- `.config/checks/lychee/lychee.toml` owns link-check behavior. Its supply
  declaration maps the executable to the official `lychee-bin` wheel; the
  development dependency and `uv.lock` own version and artifact identity.
- `.config/checks/ci/hosted-observation.toml` owns hosted provider observation envelopes; the `hosted_observation` Nox session records GitHub/GitLab provider facts or tool-discovery state without claiming repository proof, hosted CI success, or remote publication.
- `.config/checks/format/selection.toml` owns fail-closed executable-carrier
  admission and file-format boundary checks; `uv run --frozen --offline python -m nox -s format_selection`
  is the reusable runner.
- `.config/checks/architecture/projection.toml` owns architecture projection
  drift checks from `.config/checks/architecture/models/` source to generated Mermaid. The generated
  diagram is review aid, not architecture truth.
- `src/ethos/contracts/artifacts/topology.toml` owns generated-state location
  and lifecycle rules, interpreted by its adjacent product module. No parallel
  local-state configuration is maintained under this directory.
- `.config/release/supply-chain.toml` selects the built-wheel subject, SPDX
  output and claim boundary. Mise owns the Syft version and artifact checksums.
  SBOM generation does not establish publication, signing or SLSA conformance.
- `tools/ci/scripts/` holds reusable runner bootstrap logic; hosted CI YAML is
  only a provider projection that calls these scripts.
- `system/gates.toml` owns each gate's identity, profile, executable boundary,
  evidence class, and proof-floor membership. Native configuration and supply
  files remain the unique owners of tool-specific policy and versions.

## Root discovery and remaining migration boundaries

Placement follows the actual consumer, not a blanket root-file exemption.

- Python and npm manifests remain beside their ecosystem lockfiles at the
  workspace boundary. Native Git metadata and attributes retain their Git scope.
- `ruff.toml` preserves native discovery through `extend`. Its cache binding
  stays root-relative because automatic discovery and explicit configuration
  resolve inherited relative paths differently. Rules exist only in the nested
  policy; the root entry does not copy them.
- `noxfile.py` is a small native entrypoint, not another session implementation.
- `.gitlab-ci.yml` is a generated provider entrypoint. Its meaning comes from
  the CUE source and native inputs, not separately authored YAML.
- `.gitleaks.toml` contains only a native reference to the nested secret policy.
  It preserves discovery and the installed hook across the cutover without
  duplicating rules. Consumers run from the repository root; a missing or
  malformed referenced policy is rejected.
- [The optional pre-commit configuration](checks/hooks/pre-commit.yaml) invokes
  existing Nox checks. Run it with an explicit `--config` path; no root copy
  is retained. Do not install it over the ETHOS-owned Git hook.
- README, contribution guidance, license and changelog are reader entrypoints
  or project records, not tool-policy configuration.

Mise uses native nested discovery through [its configuration](mise/config.toml)
and [lockfile](mise/mise.lock) in this directory. Root copies are not retained.

## Optional pre-commit checks

The optional framework is a developer convenience, not the full proof or the
installed Git hook. Its commands call existing Nox owners rather than defining
another quality policy. From the repository root:

```bash
uv run --frozen --offline pre-commit run --config .config/checks/hooks/pre-commit.yaml --all-files
```

The source-bound `config_quality` Nox session validates this same native YAML.
Git hook installation remains owned by `ethos hook install`.

## Boundary rule

Do not duplicate the same policy in multiple files. If a provider surface needs a
policy, make it invoke the owning config or script instead of re-stating the
policy inline.

## Generated/local state topology

Configuration under `.config/checks/` owns policy only. Runtime caches and
local generated outputs must use semantic ignored homes: `.cache/local-state/`
for host-local coordination, `build/runtime/tool-cache/<tool>/` for tool caches,
the project `.venv/` for the one uv-locked Python environment,
`build/runtime/work/<provider>/` for provider emulator work state,
`build/evidence/` for machine evidence, `build/ethos/` for ETHOS machine
projections, and `build/artifacts/<kind>/` for local package/build outputs.
Root cache directories such as `.import_linter_cache/`, `.pytest_cache/`,
`.ruff_cache/`, `.uv-cache/`, and root `dist/` are denied residue, not owners.
