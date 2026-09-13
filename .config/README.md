# Configuration Layout

`.config/` holds tool-native configuration and hosted-runner setup. It is a
configuration plane, not a truth center.

## Separation of concerns

- `pyproject.toml` is limited to Python package/workspace metadata and uv wiring.
- `.config/checks/pytest/pytest.ini` is the pytest config owner and points pytest runtime cache to `build/runtime/tool-cache/pytest`, not `.config/`. Owner scripts pass it with `-c` and `--rootdir=.` so pytest still evaluates the repository subject.
- `ruff.toml` is the sole native Ruff policy owner for IDEs, hooks, CI, agents, and direct invocation. Its repository-root placement gives every per-file glob one truthful evaluation base while retaining checkout-relative runtime cache routing.
- `.config/checks/<concern>/` holds reusable tool payloads by concern.
- Root `noxfile.py` owns the executable Python lint proof surface inside the
  single uv-locked `.venv`: unsuppressed Ruff check and Ruff format check,
  both bound to root `ruff.toml`. Nox creates no second
  environment, and Ruff caches remain under `build/runtime/tool-cache/ruff/`.
  Root `pyproject.toml` remains free of Ruff policy.
- `.config/checks/coverage/coverage.ini` owns Python line-and-branch measurement; `.config/checks/coverage/policy.toml` owns the required hard floor. Default proof, full proof, and local CI enforce that same floor against current-HEAD evidence. Generated coverage data and XML go to `build/evidence/quality/tests/coverage/`, pytest JUnit evidence goes to `build/evidence/quality/tests/pytest/`, pytest cache goes to ignored `build/runtime/tool-cache/pytest/`, and pytest temporary directories default outside the repository so fixture roots cannot masquerade as repository truth. Pytest policy stays in `.config/checks/pytest/pytest.ini`; root `pyproject.toml` carries only the pytest discovery cache routing invariant for bare pytest and IDE invocation.
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
- `.config/checks/deptry/policy.toml` owns dependency hygiene policy; `tools/ci/scripts/run-dependency-hygiene.sh` runs `deptry` per Python distribution so package metadata is checked without treating the workspace root as a runtime package.
- `.config/checks/schema/jsonschema.toml` owns JSON Schema metaschema hygiene; `uv run --frozen --offline python -m nox -s schemas` validates tracked schema documents while command payload validation stays in ETHOS command tests and runtime checks.
- `.config/checks/security/audit.toml` owns the native dependency audit boundary. The `vulnerabilities` Nox session calls `tools/ci/dependency_audit.py` to audit Python and npm locks, retaining bounded native observations and one input-bound verdict. Online security guards package delivery without making offline tests depend on advisory availability; hosted CI and publication remain separate claims.
- The root `.gitleaks.toml` owns secret-scanning policy; `.config/checks/secrets/supply.toml` owns its native binary identity and digests. `tools/ci/scripts/run-secrets-scan.sh` obtains verified project-local supply through `tools/ci/toolchain/native.py` and passes the policy explicitly. Hosted proof uses the same supply owner; neither path installs system files or trusts ambient scanner bytes.
- `tools/ci/repository_hygiene.py`, invoked through the `repository_hygiene` Nox session, owns cross-file hygiene such as tracked-file size, LF endings, final newline, JSON parseability, merge-conflict markers, and the zero-suppression invariant.
- `.config/ci/templates/hosted/` owns provider CI template sources.
  `.github/workflows/ci.yml` and `.gitlab-ci.yml` are checked projections over
  those templates; `uv run --frozen --offline python -m nox -s ci_templates` is the drift gate.
- `.config/ci/emulators/` owns local provider emulator config for `act` and
  `gitlab-ci-local`. Emulator wrappers emit local evidence only and must not
  claim hosted GitHub or GitLab status.
- `.config/checks/github/actionlint.toml` owns GitHub workflow syntax policy;
  `tools/ci/scripts/run-actionlint.sh` executes the provider syntax gate and
  falls back to the pinned upstream GitHub release binary when no local
  `actionlint` is installed.
- `.config/checks/lychee/lychee.toml` owns link-check behavior while
  `.config/checks/lychee/supply.toml` owns the downloaded binary identity and
  archive digests used by hosted runners.
- `.config/checks/ci/hosted-observation.toml` owns hosted provider observation envelopes; the `hosted_observation` Nox session records GitHub/GitLab provider facts or tool-discovery state without claiming repository proof, hosted CI success, or remote publication.
- `.config/checks/format/selection.toml` owns fail-closed executable-carrier
  admission and file-format boundary checks; `uv run --frozen --offline python -m nox -s format_selection`
  is the reusable runner.
- `.config/checks/architecture/projection.toml` owns architecture projection
  drift checks from `.config/checks/architecture/models/` source to generated Mermaid. The generated
  diagram is review aid, not architecture truth.
- `.config/checks/local-state/audit.toml` owns local/generated state boundary
  checks. Runtime state remains ignored unless promoted into reviewed evidence.
- `.config/release/supply-chain.toml` binds the Syft version and archive checksums to the exact built
  wheel and SPDX 2.3 JSON output. Provenance and signing remain provider release
  concerns until real hosted receipts exist.
- `tools/ci/scripts/` holds reusable runner bootstrap logic; hosted CI YAML is
  only a provider projection that calls these scripts.
- `system/gates.toml` owns each gate's identity, profile, executable boundary,
  evidence class, and proof-floor membership. Native configuration and supply
  files remain the unique owners of tool-specific policy and versions.

## Root exceptions

Some root files remain because tools or repository substrates require root-native
discovery: `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE`,
`pyproject.toml`, `uv.lock`, `.gitignore`, `.gitleaks.toml`, `.pre-commit-config.yaml`,
`.gitlab-ci.yml`, `package.json`, and `package-lock.json`. These are admitted root surfaces, not permission to move
reusable gate policy back into the root.

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
