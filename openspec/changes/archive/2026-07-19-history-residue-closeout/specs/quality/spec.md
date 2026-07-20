## ADDED Requirements

### Requirement: Rules V2 migration is lossless for active policy

ETHOS SHALL expose the advertised Rules V2 migration through the public command
plane and SHALL preserve active non-legacy policy, including the complete
`[quality]` tree, while normalizing legacy rule keys.

#### Scenario: A mixed-generation rules file is migrated

- **WHEN** `ethos rules migrate` evaluates a file containing legacy rules and
  active quality, source-budget, and gate policy
- **THEN** dry-run reports the complete target without modifying the file
- **AND** authorized apply with the expected current HEAD preserves the parsed
  active policy and converts `paths`, `requires`, and `evidence` to V2 keys.

#### Scenario: Migration input is ambiguous or stale

- **WHEN** the rules file is unparsable, write admission fails, authorization is
  absent, or expected HEAD does not match
- **THEN** migration fails closed without rewriting the file.

### Requirement: Non-authoritative same-machine performance evidence is not a product gate

ETHOS SHALL NOT ship a same-machine timing and token-budget evidence stack as a
product quality gate when it has no trust-bearing consumer, reproducibility
contract, or provider-neutral admission boundary.

#### Scenario: The retired performance evidence stack is inspected

- **WHEN** command, tool, policy, package, test, and runner surfaces are audited
- **THEN** `ethos quality performance` is not registered
- **AND** its former policy file, Python owner, shell runner, tool declaration,
  and dedicated tests are absent
- **AND** the default proof floor still retains the declared lint, type,
  coverage, module-layout, docstring, configuration, shell, format, hygiene, and
  other hard quality owners.

#### Scenario: Performance evidence is proposed again

- **WHEN** a later change needs executable performance evidence
- **THEN** it requires a new declared tool contract, reproducible measurement
  boundary, typed report, consumer, and proof policy
- **AND** it does not restore the retired command through a compatibility shim,
  alias, or copied historical implementation.

## MODIFIED Requirements

### Requirement: Configuration and Script Quality Gates

ETHOS SHALL make configuration and runner-script quality executable through
reusable owner scripts rather than provider-specific CI inline policy, and the
same owner scripts SHALL participate in the default ETHOS proof floor.

#### Scenario: Python tool policy is owned outside the repository root

- **WHEN** the Python lint or Python test gate executes
- **THEN** ETHOS invokes the reusable owner scripts under `tools/ci/scripts/`
- **AND** Ruff policy is read from `.config/checks/ruff/ruff.toml`
- **AND** pytest configuration is read from `.config/checks/pytest/pytest.ini`
- **AND** the repository root does not contain `ruff.toml` or `pytest.ini`
- **AND** adopter CI scaffolds do not assume the product repository's Ruff, pytest,
  or owner-script surfaces

#### Scenario: Product docs may reference bounded owner scripts

- **WHEN** `ethos quality command-examples --json` scans active product docs
- **THEN** ETHOS admits documented `tools/ci/scripts/*.sh` examples as bounded
  repository-owned runner-script surfaces
- **AND** arbitrary `tools/**` command roots remain unknown command examples

#### Scenario: TOML and YAML configuration gates execute through owner scripts

- **WHEN** hosted CI or `ethos quality toml --json` / `ethos quality yaml --json` runs
- **THEN** ETHOS invokes the reusable configuration lint script
- **AND** TOML files are parsed, checked for exactly one final newline, checked
  for trailing whitespace, formatted with the configured Taplo policy, and linted
  with Taplo
- **AND** YAML files are linted with the configured Yamllint policy
- **AND** `.gitlab-ci.yml` does not duplicate Taplo or Yamllint policy inline

#### Scenario: Shell quality executes through the owner script

- **WHEN** hosted CI or `ethos quality shell --json` runs
- **THEN** ETHOS invokes the reusable shell lint script
- **AND** ShellCheck policy is read from `.config/checks/shell/.shellcheckrc`
- **AND** `.gitlab-ci.yml` does not duplicate ShellCheck policy inline

#### Scenario: Tool catalog exposes active configuration gates

- **WHEN** `system/tools.toml` is inspected
- **THEN** TOML, YAML, and shell concerns are marked active with their owning
  config path and reusable gate script
- **AND** planned tool entries do not masquerade as active gates

#### Scenario: Default proof consumes the active quality floor

- **WHEN** `ethos prove --json` builds its default action graph
- **THEN** the graph includes TOML, YAML, shell, Python lint, Python type,
  docstring, module-layout, Python size, unit/coverage, and format-policy gates
- **AND** CI, pre-commit, and proof invoke reusable owner scripts instead of
  copying tool command policy into provider projections

#### Scenario: Report exposes hard quality-floor gaps

- **WHEN** a product hard quality gate such as Python size, module layout,
  coverage, type policy, or public-surface docstrings reports required gaps
- **THEN** `ethos report --json` includes those gaps in its blocking
  `required_gaps`
- **AND** the report state is not ready
- **AND** the report payload includes a `hard_quality_floor` read model with the
  contributing gate verdicts
- **AND** next actions point to the concrete standalone quality command instead
  of implying full proof can close the gap

#### Scenario: Coverage quality read model reports the active floor

- **WHEN** `ethos quality coverage --json` runs
- **THEN** ETHOS reports the coverage policy source, current hard floor, aspirational
  floor, branch coverage requirement, configured source paths, configured
  `fail_under`, owner script, and latest coverage artifact summary when present
- **AND** the command reports required gaps when policy or config is missing,
  `fail_under` diverges from the hard floor, branch coverage is disabled while
  required, the latest artifact is missing or malformed, or latest coverage is
  below the hard floor
- **AND** when the Python test owner script holds the coverage evidence write
  lock and the latest artifact is temporarily absent, the command reports the
  writer as in-progress advisory state rather than a stale coverage failure
- **AND** the command remains read-only and does not replace the reusable Python
  test gate owner script

### Requirement: Repository Hygiene Gate

ETHOS SHALL make repository-shape hygiene visible through one owner script and a
separated policy file so host-local residue, text-shape drift, merge markers,
large tracked files, malformed JSON, and forbidden stash guidance cannot hide in
Git, global ignores, provider projections, or hook-local behavior.

#### Scenario: Hidden root host-local residue fails closed

- **WHEN** `tools/ci/scripts/run-repository-hygiene.sh` runs
- **THEN** the gate reads `.config/checks/repository-hygiene/policy.toml` as the
  policy owner
- **AND** globally ignored root host-local files such as `.DS_Store`,
  `Thumbs.db`, and `Desktop.ini` fail with a required hygiene error
- **AND** the gate reports the residue without deleting, stashing, or promoting
  it into repository truth
- **AND** CI providers, pre-commit hooks, and local CI call the owner script
  instead of duplicating the policy body.

#### Scenario: Historical carriers are not active stash guidance

- **WHEN** repository hygiene scans Chronicle records under `evidence/chronicle/`
  or archived OpenSpec carriers under `openspec/changes/archive/`
- **THEN** final-newline, line-ending, conflict-marker, large-file, and structured
  carrier checks continue to apply
- **AND** the stash-guidance check does not reinterpret historical records as
  current operating instructions
- **AND** positive stash guidance in active docs, rules, plans, or OpenSpec
  carriers remains blocked.

## REMOVED Requirements

### Requirement: Structural Blank-Line Contract

**Reason:** The repository-wide reader retained a custom cosmetic blank-line
policy across native and fallback carriers after its rollout closed. Its JSON,
INI, Jinja, plain-text, Shell-outer, and OpenSpec coverage is intentionally
retired rather than misrepresented as a correctness or trust-boundary gate.

**Migration:** Markdown, TOML, YAML, Python, and Shell remain governed by
Markdownlint, Taplo, Yamllint, Ruff, and ShellCheck respectively. Repository
hygiene continues to enforce durable text integrity such as final newlines,
line endings, parseability, and conflict-marker absence. These owners do not
preserve the retired universal one-blank-line constraint.

### Requirement: Structural blank-line contract

**Reason:** This duplicate requirement described the same intentionally retired
cosmetic constraint, including fallback checks over active OpenSpec carriers.

**Migration:** Active OpenSpec carriers remain governed by official OpenSpec
validation rather than a second repository-specific whitespace parser; official
validation does not inherit the retired blank-line policy.
