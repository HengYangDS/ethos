---
subject: ethos:workflow-runtime-frameworks-20260709
role: research
state: active
relations:
  informs: docs/architecture/workflow-runtime.md, openspec/changes/archive/2026-07-09-adopt-ethos-native-workflow-runtime
---

# ETHOS Framework Research Report: Comet, OpenSpec, and Adjacent SDD/Agent Workflow Systems

Date: 2026-07-09
Repo context: ETHOS product repository. This document promotes a source-read research snapshot into repository truth.
Source snapshot root during research: `/tmp/ethos-framework-snapshots`.

## Executive verdict

The previous binary framing, "Comet vs OpenSpec", is too shallow. Source reading shows they occupy different layers:

- **OpenSpec** is a durable spec/change/archive carrier with validation, schema/artifact graph, and store support.
- **Comet 0.4** is a richer **workflow runtime + skill harness + evaluation/control-plane** that uses OpenSpec as one carrier and Superpowers as one method pack.
- **ETHOS should not simply pick one**. The best direction is: keep OpenSpec as a mandatory spec/change carrier adapter, but absorb Comet-like runtime mechanisms into ETHOS's own kernel-command plane.

In short: **Comet is more extensible as a workflow system; OpenSpec is more appropriate as a spec carrier. ETHOS should become the governing kernel above both.**

The more fundamental conclusion is that ETHOS should not govern frameworks as
objects of attachment. It should govern the **passage from question to
repository law, bounded refusal, archive, or retirement**. Practice claims are
evolution carriers inside that passage: they name what practice is being
asserted, where its boundary is, what would falsify it, which candidates were
compared, which experiment and evidence were used, what commitment effect is
proposed, and whether the practice introduces, composes with, refines,
supersedes, retires, archives, or is rejected from governed commitments.

## ETHOS non-negotiable boundary

From live repo + memory:

- `dev` is accepted_root / observe-only; tracked mutation belongs in `work/*` lanes.
- ETHOS terminal thesis is single kernel / profile adapters, not external workflow replacement.
- Current semantic owner mapping: Backlog = projection/UI/intake; Change Claim = lifecycle atom; OpenSpec = spec projection; Mission = feedback/exhaustion loop; Work Lane = isolated execution lane.
- Official OpenSpec artifacts should come from official CLI/workspace; external frameworks should plug into admission and proof rather than replace repository truth.

Therefore, any adopted mechanism must become **adapter/profile/method pack/proof evidence** under `ethos status -> plan -> prove -> land -> publish`, not a second command plane.

## Framework matrix

| Framework | Source-read core | Truth/state carrier | Extension model | Best ETHOS use | Main risk |
|---|---|---|---|---|---|
| Comet 0.4 | `domains/comet-classic`, `workflow-contract`, `bundle`, `engine` | `.comet.yaml`, `.comet/run-state.json`, `.comet/state-events.jsonl`, OpenSpec changes | SkillBundle, workflow contract, output schemas, eval, platform installers | Absorb runtime patterns: phase guards, resumability, skill eval, state event log | Creates second lifecycle if `.comet` becomes truth |
| OpenSpec 1.5 | `src/core/archive.ts`, `artifact-graph`, schemas, stores | `openspec/specs`, `openspec/changes`, `.openspec.yaml`, stores | schemas/workflows/profiles; commands/skills | Keep as mandatory spec/change carrier adapter | Insufficient alone for long-running execution/eval |
| GitHub Spec Kit | `workflows/speckit/workflow.yml`, `workflows/engine.py`, extensions/presets | `.specify`, specs/plans/tasks; workflow run state | extensions, presets, bundles, integrations | Borrow extension/preset taxonomy and workflow YAML shape | Workflow `requires` is advisory; shell steps run with user privileges |
| BMAD Method | module registry, installer, workflow map, agent-as-code docs | `_bmad` manifest/docs, generated skill modules | modules, official registry, role agents | Borrow scale-adaptive planning and agent role handoff vocabulary | Heavy process theater; weak machine proof |
| Superpowers | `skills/*/SKILL.md`, hooks | skills + optional hooks | skill pack only | Keep as method pack: TDD, debugging, subagents, worktrees, verification | Textual enforcement unless wrapped by ETHOS proof/guards |
| Task Master | `scripts/modules/task-manager`, MCP tools, `.taskmaster` | task JSON, tags, state/config | MCP + CLI task operations | Borrow task graph, dependency/next-task selector, tag contexts | Separate task store conflicts with Backlog/Work Lane if adopted directly |
| Agent OS | command prompts + standards profiles | `agent-os/standards`, product/spec docs | profiles and standards injection | Borrow concise standards index/injection for ETHOS docs/skills | Highly interactive; weak machine gates |
| OpenSPDD | REASONS Canvas templates, cross-tool command generator | `spdd/analysis`, `spdd/prompt` | embedded templates per AI tool | Borrow REASONS-style design contract sections where useful | Mostly prompt templates; little machine verification |
| Shotgun | TUI/router, codebase indexing, staged specs | `.shotgun` local/cloud specs | specialized router agents/product UX | Borrow research->spec->plan->tasks->export UX and codebase-aware indexing idea | Product/runtime/cloud, likely too large as ETHOS dependency |
| fspec | Gherkin/ACDD, work units, coverage, checkpoints | `spec/*.json`, feature files, coverage files | many CLI commands, TUI | Borrow scenario coverage, checkpoints, command-maintained coverage links | Huge parallel spec system; would duplicate ETHOS Backlog/OpenSpec/Claim |

## Comet 0.4 findings

Comet is not just an OpenSpec wrapper. It has several kernel-worthy mechanisms:

1. **Classic phase state**
   - `ClassicState` tracks workflow/profile, phase, build mode, isolation, verify mode/result, verification report, branch status, handoff context/hash, migration version.
   - Phases: `open`, `design`, `build`, `verify`, `archive`.
   - Profiles: `full`, `hotfix`, `tweak`.

2. **Explicit transition table**
   - `open-complete`, `design-complete`, `build-complete`, `verify-pass`, `verify-fail`, `archive-reopen`, `archived`, `preset-escalate`.
   - State transition effects are machine-recorded.

3. **Guarded transitions**
   - Guard checks assert artifacts exist, tasks are done, design handoff hash is current, language matches configured language, build/verify commands pass, branch status handled, etc.
   - Guards can `--apply` transitions instead of trusting agent claims.

4. **Append-only event log**
   - `.comet/state-events.jsonl` records source, event, before/after state, effects, timestamp.
   - This is close to ETHOS Chronicle semantics.

5. **Run state separate from workflow state**
   - `.comet/run-state.json` stores run id, skill hash, orchestration mode, current step, pending action, trajectory/context/artifacts/checkpoint refs, status, retries.
   - Good separation: human-authored-ish YAML vs machine-owned run state.

6. **Workflow contract**
   - Node model: control/producer/action/handoff/guardrail.
   - Operations: require/augment/override/disable.
   - Enforcement: guarded/handoff-guarded/evidence-only/advisory.
   - Output schemas define artifacts and evidence.
   - Builtin five-phase workflow is normalized into protocol + edges + eval expectations.

7. **SkillBundle platform**
   - Bundle manifest supports skills, rules, hooks, scripts, references, assets, agents, platform overrides, engine.
   - Validator rejects path escapes, symlinks, undeclared hook scripts, invalid engine packages.
   - Compiler produces deterministic IR and hash.

8. **Eval/control-plane**
   - Eval result schema records pass@k, weighted score, instability gap, failures, reports.
   - Factory control plane validates generated skill package files, scripts, eval manifests, workflow protocol, decision points, recovery docs.

### Comet limitations for ETHOS

- `.comet.yaml` would be a second lifecycle store if adopted directly.
- Its phase names do not match ETHOS transition semantics (`status/plan/prove/land/publish`, Work Lane, claim/evidence/chronicle).
- It infers build commands generically (`npm run build`, Maven, Cargo), while ETHOS proof gates are repo-specific and already governed.
- It depends on OpenSpec/Superpowers assumptions; ETHOS should own adapters, not inherit them.

### Comet mechanisms ETHOS should absorb

- Transition table and guard refs as first-class kernel data.
- Machine-owned run state separated from human/governance state.
- Append-only state event log mapped to Chronicle.
- Handoff context with hashes for agent/subagent handoffs.
- Workflow contract node model and operation types, but renamed to ETHOS terms.
- Skill bundle validation and deterministic IR/hashing for skill portfolio governance.
- Eval metrics (pass@k, pass^k, instability gap) for skill evolution.

## OpenSpec findings

OpenSpec remains the cleanest carrier for specs and deltas:

- Archive command validates, applies spec updates, moves change to archive, supports JSON non-interactive failure diagnostics.
- Change metadata schema validates schema, created date, goal, affected areas, initiative link.
- Artifact graph supports schema-defined artifacts, dependencies, completion state, apply tracking.
- Store support allows planning in repo of its own / cross-repo spec carrier.
- Global config supports profile/delivery/workflows.

ETHOS should keep official OpenSpec, but wrap it:

- `openspec/specs` = accepted behavioral spec projection.
- `openspec/changes` = spec delta carrier.
- `ethos openspec` = adapter that validates lifecycle, archive fusion, evidence/claim refs, and no silent delta loss.

## Spec Kit findings

Spec Kit is strong in ecosystem extensibility:

- `workflows/speckit/workflow.yml` expresses specify -> gate -> plan -> gate -> tasks -> implement.
- Workflow engine supports sequential steps, gates, branching, loops, fan-out/fan-in, state persistence/resume.
- Extensions and presets are cleanly separated:
  - Extensions add capabilities/commands.
  - Presets replace templates/commands to change behavior.
- Integration system supports many agents and skills/commands.

Caveat: workflow `requires` is explicitly advisory, not a security boundary; shell steps run with user privileges. ETHOS can borrow the grammar, but must attach real admission/proof gates.

## BMAD / Superpowers findings

BMAD offers broad role/workflow coverage, but mostly as generated skills and docs. Best borrowed concepts:

- Scale-adaptive workflow depth.
- Role-specific artifact handoffs.
- Implementation readiness gate.
- Module registry/installer metadata.

Superpowers is already a high-signal method pack:

- TDD with red/green/refactor discipline.
- Systematic debugging.
- Subagent-driven development with implementer/reviewer loop.
- Git worktree isolation.
- Verification-before-completion.

ETHOS should not reimplement all method prose; instead, treat these as method packs invoked through ETHOS-admitted workflow nodes and proof.

## Task Master / Agent OS / OpenSPDD / Shotgun / fspec findings

- **Task Master**: task JSON/tagged contexts/dependencies/next-task selector are useful, but direct adoption conflicts with ETHOS Backlog and Work Lane. Borrow dependency and prioritization algorithms.
- **Agent OS**: standards discovery/index/injection is useful for reducing context load; borrow concise standards index rather than its interactive command flow.
- **OpenSPDD**: REASONS Canvas is a good design-contract template: Requirements, Entities, Approach, Structure, Operations, Norms, Safeguards. Borrow as optional design facet, not lifecycle.
- **Shotgun**: strongest as product UX pattern: codebase-aware research -> spec -> plan -> tasks -> export, router/TUI. Too productized/cloud/runtime-heavy for dependency.
- **fspec**: strongest in Gherkin/ACDD, checkpoints, coverage mapping from scenarios to tests/code. Borrow coverage/traceability ideas for ETHOS Evidence/Claim, not its whole spec system.

## Recommended ETHOS architecture

### Layer 0: ETHOS kernel (unchanged authority)

Authority -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle.

This chain is the auditable engineering handle for the deeper governed passage:
question -> boundary -> test -> judgment -> inscription or release.

### Layer 1: Practice-claim evolution carrier

Represent reusable methods and framework lessons as governed practice claims:

- subject, question, claim, boundary, and falsifiers;
- candidate practices or carriers;
- experiment protocol and evaluation record;
- commitment targets if the claim passes;
- fate records: introduce, compose, refine, supersede, retire, reject, or archive.

This layer prevents a false binary such as "Comet vs OpenSpec" from becoming
the model. OpenSpec can remain a carrier while Comet-style runtime ideas,
Spec-Kit-style workflow grammar, Task-Master-style task graphs, fspec-style
scenario coverage, and method packs are selected or rejected by relation to the
same practice claim.

### Layer 2: ETHOS workflow runtime (new, Comet-inspired)

Implement under ETHOS names, not `.comet` names:

- `workflow_run` / `transition_run` state.
- machine-owned run JSON under ETHOS evidence/local-state boundary.
- transition table: status/plan/prove/land/publish plus Work Lane actions.
- guard refs tied to existing quality gates and proof commands.
- append-only chronicle events with before/after/effects.
- handoff context packages with SHA256 provenance.

### Layer 3: carriers/adapters

- OpenSpec adapter: spec/change/archive carrier.
- Backlog adapter: intake/projection/task UI.
- Task graph adapter: dependency and next-task scoring (from Task Master ideas).
- Scenario/coverage adapter: Gherkin/coverage mapping (from fspec ideas).

### Layer 4: method packs

- Superpowers/BMAD/OpenSPDD methods remain method packs.
- ETHOS may route them via workflow nodes with explicit output schemas and proof requirements.

### Layer 5: skill/eval governance

- SkillBundle-like manifest for ETHOS repo-local skill packages.
- Deterministic IR + hash.
- Eval runs with pass@k / pass^k / instability gap for skill evolution.
- Projection drift checks for vendor surfaces.

## Concrete adoption plan

### Milestone 1: OpenSpec change for evaluation outcome

Create an ETHOS Work Lane and OpenSpec change, e.g. `evaluate-workflow-runtime-frameworks`.
Scope: record decision and prototype boundaries, not full migration.

### Milestone 2: Runtime prototype

Prototype a minimal ETHOS-native transition event log:

- current command status reads live repo state.
- `plan/prove/land` guard refs produce transition effects.
- append event with before/after/effects and proof refs.
- no `.comet.yaml`; use ETHOS-owned schema/location.

### Milestone 3: Handoff prototype

Add a deterministic handoff package:

- source refs: OpenSpec change, plan, tasks, evidence, claim.
- SHA256 of source files.
- subagent/reviewer prompt package.
- stale-handoff detection when source hash changes.

### Milestone 4: Skill bundle/eval prototype

For repo-local skills:

- manifest -> deterministic IR.
- path/symlink/escape validation.
- eval metadata model: task, treatment, pass@k, instability gap.
- integrate with `ethos playbooks check` / skill portfolio gates.

### Milestone 5: Decision record

Record final decision:

- Keep OpenSpec as spec carrier.
- Do not adopt Comet directly as runtime.
- Absorb Comet runtime patterns under ETHOS kernel.
- Borrow Spec Kit extension/preset taxonomy.
- Borrow Task Master dependency selector, Agent OS standards index, fspec coverage mapping as optional adapters.

## Final recommendation

Adopt **Comet's mechanisms**, not Comet as authority.

OpenSpec remains necessary but insufficient. Comet shows the missing layer ETHOS should build: phase/run state, guard transitions, recovery, skill composition, and evaluation. However, ETHOS should implement this as an ETHOS-native governed runtime so the command plane, proof, claims, Work Lanes, and Chronicle remain the center.

## Promotion Boundary

This research document is now the active evidence-backed comparison record for
the workflow-runtime adoption decision. It is not itself a runtime contract. The
promoted product contract is the combination of `docs/architecture/workflow-runtime.md`,
`system/workflows.toml`, schemas under `system/schemas/`, OpenSpec deltas, tests,
claims, and chronicle evidence.

Status: see front matter.

Purpose: compare Comet 0.4, OpenSpec, Spec Kit, Task Master, BMAD,
Superpowers, Agent OS, OpenSPDD, Shotgun, fspec, and adjacent SDD/agent
workflow systems as practice carriers so ETHOS can choose what to introduce,
compose, refine, supersede, retire, reject, or archive without adopting an
external lifecycle authority.

See also: [Workflow Runtime](../architecture/workflow-runtime.md),
[Evolution Campaign](../governance/evolution-campaign.md), and
[OpenSpec Governance](../governance/openspec-governance.md).
