# Design

## Context

See [proposal.md](proposal.md). Design revision 5.3, D14
(`build/runtime/work/architecture-realization/design.md`), states the principle. The route splits
its step 2 at this proposal under PDC 569-573. This Change is the kernel. `shared-quality-floors`
converts the shared Nox floors into providers and carries the route's deletions.

Constraints:

- **Budget.** `python_product` is 69,986 of 70,000 at `ebe90676a`, so the product side must stay
  within 14 effective lines.
- **Predecessor compatibility.** The installed hook re-admits the landing with its own compiler and
  packaged data. The lane runs the candidate as a source runner, and reads product resources beside
  its own package (`repository/release/resources.py` `canonical_resource`). Admission requires equal
  policy digests and nodes (`adapters/mutation/proof_admission.py`).
- **Bindings follow execution.** A composed floor binds its provider module's bytes under `@ethos/`
  (`repository/policy/quality/sources.py` `provider_module_sources`), and those bytes are the code
  that runs.

## Goals / Non-Goals

**Goals:**

- A repository's obligations are one function of what ETHOS's rules read, ETHOS's included: the
  shared obligations its authored carriers select, plus the gates it declares.
- Every name, profile id, registry path, location and history leaves those obligations unchanged.
- ETHOS's own tree proves the shared quality floor with product-owned evidence.

**Non-Goals:**

- Converting the shared Nox floors into providers, CUE in `source-format`, formatter increments,
  waivers, link and byte-validity floors, the one-owner check of D14 consequence 3, and D12's
  declared supply with the runtime-authority fact. These belong to `shared-quality-floors`.
- The source-budget ratchet of D13. It is stated with its first application, in the release Change
  that follows this Change.
- Retiring `javascript-lint`, whose analysis `code-static` now also performs for ETHOS, and folding
  ETHOS's own `skills` declaration into the shared one. Both are deletions of
  `shared-quality-floors`.

## Decisions

### 1. Two registries, two owners

The packaged `system/gates.toml` keeps the obligations ETHOS owns for every repository: the seven
floors that declare `required_for_paths` (`docs-registry`, `openspec`, `markdown-links`,
`config-quality`, `markdown-lint`, `source-format`, `prose`), `openspec`'s dependency `schemas`, and
`skills`, which the starter rules require of every repository. Each entry states
`profile = "repository"` and `tool_adapter = "ethos"`, the form composition wrote into every
adopter's policy. The rewrite is therefore removed, and the declaration is what runs.

ETHOS's other 29 gates move to `system/repository-gates.toml`, which `.ethos/profile.toml` names;
its own `skills` declaration stays among them, unchanged, until `shared-quality-floors`. The
repository-paradigm requirement that named only `profile.toml` or "the packaged registry" now names
the registry file a profile selects, which is what the films already do with their own
`system/gates.toml`.

The dependencies of `unit-architecture` on `schemas` and `config-quality`, and of
`github-workflow-syntax` on `config-quality`, are dropped. A declaration validates its dependencies
within itself, and composition supplies both gates. The dropped dependencies ordered checks that
write no files.

### 2. One fact selects where shared data come from

`product_source` decided by registry path and merge base. It is replaced by one fact about the
subject's carriers: its `pyproject.toml` declares the distribution of the running product. When the
fact holds, the packaged registry is read from the subject tree's `system/gates.toml`. Each
`@ethos/<module>` source is read from `src/ethos/<module>`, and `@ethos/resources/<x>` from `<x>`,
the inverse of the wheel projection. Otherwise both come from the running package, as for every
repository today.

The fact is invariant under name, profile id, registry path, location and history. It is inert in an
ETHOS lane, where the running package is the candidate tree. When an installed ETHOS judges a tree
that builds ETHOS, the bytes it binds are the bytes that tree executes.

Alternatives rejected:

- Judging an ETHOS candidate by the predecessor's shared data. The lane executes the candidate's
  providers, so the predecessor's bytes would bind code that did not run.
- A declared self-supply field in the profile. It would restate what `pyproject.toml` already
  declares.

### 3. Dependency acceptance by content

A captured audit names the product policy it composed. Acceptance admits a capture that names the
judging product's portable projection or the subject's own projection. Composition only adds the
product's dispositions to the subject's (`compose_audit_policies`). Either result is therefore the
adopter result of today or the subject's own policy alone, and neither accepts more than today.

### 4. ETHOS proves the shared floor

Removing the exemption applies the quality floor to ETHOS, and `quality_verifier_gaps` requires a
behavior and a static verifier that claim every subject:

- `unit-architecture` becomes a `verified-command` gate with the verification provider
  `ethos.adapters.gates.code_quality:behavior_report`. Its native outputs are JUnit and Cobertura
  under `{native_output}`.
- `javascript-tests` verifies JavaScript behavior the same way, with JUnit and lcov from the
  session's c8. Node tests run each product module through the protocol its Python caller uses, and
  the npm launcher through stubbed `uv` and Python, because the product's own Node attempts reset
  `NODE_V8_COVERAGE`. The reporter runs in the test process, because Node's test orchestrator, which
  loads reporters, writes no V8 coverage.
- `code-static` claims every static subject through
  `ethos.adapters.gates.code_quality:static_report`, declared as a governed repository declares it.
- `.gitattributes` declares `tools/**` and `noxfile.py` with `ethos-role=tooling`. Their static
  analysis stays required, and their behavior is exercised through the tests that run them.

### 5. Values belong to the rule that states them

The shared static floor runs Ruff isolated, because Ruff rejects a configuration file beside
`--isolated`. With Ruff's isort defaults, the `I` rule imposes a value that no contract states, and
it reports 656 `I001` findings on ETHOS, whose configuration declares `force-single-line = true`.
The floor therefore passes the import-sorting values of the repository's declared Ruff configuration
as inline overrides, beside the declared target version it already reads.

### 6. One landing

The predecessor compiles the candidate as an adopter, because the candidate's registry is no longer
at the packaged path. It composes its own floors, applies the quality floor and compares the capture
with its own audit snapshot. The candidate's compiler reproduces that compile when the shared
entries, the modules the predecessor binds from its own build, the audit policy and the floor
computation are unchanged. Before the proof, both runtimes compile `resolve_proof_policies` on the
archived head and must agree. The hook reinstall after landing then selects shared data by the fact
of decision 2.

## Risks / Trade-offs

- [A JavaScript module escapes the behavior evidence] → The session's lcov must execute every
  JavaScript subject, and the pre-proof runs of `unit-architecture` and `javascript-tests` evaluate
  `quality_obligation_gaps`. A missing module blocks there, not in the proof.
- [The fact reads as an identity check] → It compares a declared carrier value, not a path, a
  profile id or a history, and the symmetry regression varies each of those.
- [Predecessor compatibility is narrow] → Any edit to a bound module, the audit policy, a shared
  entry or the floor computation would be a policy mismatch at land. Both compiles and a byte
  comparison of those paths run before the proof.
- [ETHOS's default proof runs four more floors] → Their duration is measured in the proof and
  reported.
- [Budget margin] → Product growth is measured at the archived head; a wider draft offsets in the
  same Change.
