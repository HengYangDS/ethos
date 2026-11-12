---
subject: docs:decisions
role: index
state: canonical
relations:
  canonical_for: durable decision navigation
---

# Decisions

Status: canonical navigation; records retain rationale, not current executable authority.

Purpose: find choices whose alternatives and revisit conditions remain useful across Changes.

See also: [Documentation Root](../README.md) and
[Docs Registry](../governance/docs-registry.md#directory-entrypoint-rule).

Records use `dr-<four-digit-id>-<semantic-topic>.md`. The number is a stable
decision identity, never reused or renumbered; the topic remains readable.
This README is the only navigation, not a second decision registry. It lists
every number in order: a current record is a link, and every other number is one
line with its MADR status beside the record's own word, its decision date, its
successor and the commit where its record last existed. Git keeps those records'
bytes. The linked Docs Registry owns the shared metadata, rationale and
five-section form; this entrance does not maintain another template or rule set.

- DR-0001: Generated artifact topology contract (2026-07-07). Superseded (own word: "superseded by `model-promotion`"); its rules now live in the PDC's [Model Promotion](../governance/product-design-contract.md#model-promotion), the topology declaration `src/ethos/contracts/artifacts/topology.toml` and the quality specification's "Generated Artifact Boundary"; [Generated Artifact Topology](../architecture/generated-artifact-topology.md) explains them. Record: `374d49d94^`.
- DR-0002: Documentation topology isomorphism contract (2026-07-07). Superseded (own word: superseded) by DR-0004. Record: `374d49d94^`.
- DR-0003: Proof scope compatibility contract (2026-07-08). Superseded (own word: accepted, until its deletion on 2026-08-15) by the current contract: known proof scopes and the `unknown_proof_scope` gap in `src/ethos/application/proof/report.py`, and host execution that mints no proof in [Command Plane](../reference/command-plane.md#routine-scoped-execution). Record: `374d49d94^`.
- DR-0004: Minimal semantic documentation topology contract (2026-07-08). Deprecated (own word: retired); the [Docs Registry](../governance/docs-registry.md) now owns its subject, and no replacement record was created; historical carrier [docs topology contract](../history/docs-topology-contract-20260708.md). Record: `374d49d94^`.
- DR-0005: Declarative lifecycle spine (2026-07-10). Superseded (own word: accepted, until its deletion on 2026-08-15) by the current owner of the spine, the [Declarative Lifecycle Rules](../../rules/declarative-lifecycle.md); [Declarative Governance Compiler](../architecture/declarative-governance-compiler.md#spine) explains it. Record: `374d49d94^`.
- [DR-0006: Proof trust boundary](dr-0006-proof-trust-boundary.md): why local proof and independent assurance are separate claims.
- DR-0007: Docs kernel form-invariance and adopter-parity evidence locus (2026-07-12). Superseded (own word: superseded) by DR-0004. Record: `374d49d94^`.
- DR-0008: Metric-domain budget contract (2026-07-19). Deprecated (own word: retired by the terminal owned-source contract and the quality specification); succeeded by DR-0010. Record: `374d49d94^`.
- DR-0009: Budget contract version 2 calibration (named 2026-07-19). Rejected (own word: reserved and not reassigned); DR-0008's text in `13864eb4f` named it as a record to create, it was never written, and DR-0010 rejected the metric language it would have calibrated.
- [DR-0010: Source-budget non-compensation](dr-0010-source-budget-non-compensation.md): why unrelated source classes cannot subsidize each other's growth.
- [DR-0011: Documentation portability](dr-0011-documentation-portability.md): why semantic discovery does not mandate one physical tree.
- [DR-0012: Repository paradigm](dr-0012-repository-paradigm.md): why every governed repository follows one common repository contract and which structure stays repository-owned.
- [DR-0013: Historical repair evidence reads its own policy location](dr-0013-historical-repair-policy-location.md): why moving a policy field does not reinterpret an earlier repair record.
- [DR-0014: Comparative correction](dr-0014-comparative-correction.md): why a replacement may drop an incumbent finding only when evidence outside the candidate shows it false.
- [DR-0015: Release stages follow a declared journey scope](dr-0015-release-stage-scope.md): why a prerelease advances by evidence on its declared journeys and an adopter's environment is not a release precondition. Its 0.2.0 host list is superseded by DR-0021.
- [DR-0016: Changes close on their delivered scope](dr-0016-change-closure-scope.md): why a Change archives with the tasks it delivered and how a withdrawn task stays visible until a new Change restores it.
- [DR-0017: One obligation, one owner](dr-0017-one-obligation-one-owner.md): why each obligation has one owner across ETHOS and every governed repository, and why ETHOS judges its own tree by the obligations it ships.
- [DR-0018: A historical artifact is judged by the attestation made when it was produced](dr-0018-historical-artifact-attestation.md): why a release tag publishes on the proof its own release record bound, and why a later runtime never re-judges it under its own policy.
- [DR-0019: The source budget counts code, not layout](dr-0019-layout-invariant-source-budget.md): why the Python ceilings count layout-invariant code tokens in line-equivalents, where the conversion came from, and why the test ceiling moved one step.
- [DR-0020: The product ceiling moves to 80,000 for the RC work](dr-0020-product-budget-step.md): the necessity review that took one 5,000 step after the proved duplication was removed.
- [DR-0021: Release 0.2.0 declares three journeys and narrows DR-0015's hosts](dr-0021-release-scope-0-2-0.md): why 0.2.0 drops Windows x64, conditions Homebrew and leaves the GitLab CI component unqualified, and which of DR-0015 stays in force.
- [DR-0022: From 0.3.0, builds are immutable and stages are evidence-gated channels](dr-0022-release-channels-0-3-0.md): why build identity and qualification separate, and why a declared hermetic local venue counts.
- [DR-0023: The test ceiling moves to 105,000 for the beta.8 work](dr-0023-test-budget-step.md): the necessity review that took one 5,000 test step after the proved duplication was removed.
- [DR-0024: History is rebuilt once, under one Change-local record, with originals held locally](dr-0024-history-rebuild-map.md): why one landed record authorizes a history rebuild, why the originals stay in a local side repository and only readiness and the apply read the key, and why the work lands in two landings.
