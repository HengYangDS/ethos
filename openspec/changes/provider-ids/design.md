# Design

## Context

See the [proposal](proposal.md). A gate declaration carries its providers as strings, and five
readers interpret them:

- the declaration contract (`src/ethos/contracts/gates.py`) checks only that a string starts with
  `ethos.` and holds one colon;
- the gate runner (`src/ethos/adapters/gates/verification.py`) imports the module and calls the
  attribute;
- source binding (`src/ethos/repository/policy/quality/sources.py`) turns the module part into the
  source path that a gate's policy digests;
- four places compare a string with a literal to give a provider a meaning: the two code-quality
  axes and the source-integrity verifier (`.../quality/obligations.py`), the JavaScript attempt of
  the gate runner, and the skill portfolio of `plan`;
- shared-gate composition (`.../quality/gate_composition.py`) compares a repository's declaration of
  a shared gate with the packaged one, string by string.

The installed runtime judges every landing with its own copy of these readers: the landing compares
the plan that the installed runtime compiles for the candidate head with the candidate's own plan,
and the hook admits the proof again with the installed code.

## Goals / Non-Goals

Goals:

- A declaration names a provider by an ID that survives a move of the provider's module.
- Every legacy name that a shipped or an adopter registry declares today, and that names a callable,
  keeps its behavior for one support window.
- A name that resolves to nothing refuses with one named gap before any gate runs.

Non-Goals:

- Switching the shipped registries to IDs. The installed runtime's declaration contract refuses an
  ID, so a head whose registries name IDs cannot land until the installed runtime carries this
  Change; the switch is the next landing.
- Removing a legacy name, or moving any provider module.
- A stability rule for the provider call signature, which the application package's own Change sets.

## Decisions

1. **One packaged table, read by the kernel.** `src/ethos/contracts/gate_providers.toml` holds
   `[providers]`, each ID with its `module:callable`, and `[legacy]`, each legacy name with its ID.
   `ethos.contracts.gate_providers` reads it beside itself, as the paradigm and the artifact
   topology read their tables; the wheel ships the file under the package rule that ships those, so
   no include row is added. The module imports nothing from a layer above the contracts and never
   imports a provider. An alias module was refused: the module-layout rule forbids one, and it would
   put a second name on the import path instead of into data.
2. **The declaration checks the form; the readers resolve.** A reference is `provider.<name>` in
   lower-case words joined by hyphens, or a legacy `ethos.<module>:<callable>`. Whether a name
   resolves is decided where a provider is used: the runner imports the catalog's target, source
   binding takes the target's module, and the policy names what does not resolve. A declaration
   contract that looked names up would make a registry valid or invalid by the release that reads
   it, which is the coupling this Change removes.
3. **The declared spelling stays the recorded identity.** A gate's execution identity, its policy
   fields and the `provider` key of each report keep the declared string. For a registry that still
   names legacy names, this Change therefore compiles the policy that the installed runtime
   compiles, which is what lets it land. A recorded proof also keeps naming what the repository
   declared. A gate's policy still digests the source of the module that the catalog resolves, so a
   table row that moves an ID to another module changes the gate's bound source and makes an
   earlier proof stale; the table itself is not a bound source.
4. **Meaning follows the ID.** One function returns every spelling of an ID, and the four comparing
   places use it, so a gate verifies a code axis, source integrity, the JavaScript attempt or the
   skill portfolio under either spelling. Shared-gate composition compares providers by ID, so a
   repository that redeclares a shared gate by its legacy name keeps composing after the packaged
   registry names the ID.
5. **An unresolved name is a policy gap.** `gate_provider_unresolved:<gate>:<name>` joins the
   policy's gaps, the channel that already refuses a proof whose gate source is missing, so no gate
   runs. An unresolved name binds no source. A runner that is handed such a gate directly still
   refuses it as a provider error.
6. **A legacy name adds a note.** The gate's result carries one diagnostic of severity `note` with
   the code `gate_provider_legacy_name` and the ID to declare, the form that the commit-ranges gate
   already uses for an advisory. It sits on the gate's result, not in the provider's report, so
   both spellings yield the same report, and it changes no verdict.
7. **IDs name the responsibility, not the module.** Most IDs take the name of the gate that their
   provider serves (`provider.docs-registry`, `provider.commit-ranges`). A provider that several
   gates or repositories declare is named for what it verifies: `provider.python-behavior` beside
   `provider.code-behavior`, `provider.skill-portfolio`, `provider.source-integrity`.
8. **The table lists what exists.** It maps the 21 names of the shipped registries and the two
   further names that adopter registries declare and that name a callable. One name that an adopter
   declares names no callable today and stays unmapped; its proof already blocked when the gate ran
   and now refuses when the policy is compiled.

## Risks / Trade-offs

- **The shipped registries still name legacy names after this Change.** The next landing switches
  them, together with the hosted probe that reads the test gate's report by its declared name. Its
  condition is that the installed runtime carries this Change; until then ETHOS's own proofs carry
  the legacy note. A release cut between the two landings would add that note to every adopter's
  shared gates, which no adopter declares, so both landings belong to one release.
- **The contract step is not this Change.** Removing a legacy name is Breaking. Its condition is
  that the last adopter's registry has migrated, and no earlier than the end of the support window.
- **A registry that names IDs needs a runtime with the catalog.** An earlier release refuses it,
  also on a rollback. A repository therefore migrates its registry once the release it would roll
  back to carries the catalog, and restores the legacy names before an older rollback.
- **The support window is stated here before the distribution specification defines one.** The
  plan proposes two weekly batches for the fleet; when the distribution specification states the
  fleet's window, this requirement should refer to it instead of restating a length.
- **A target can drift from its table row.** The table-driven test imports every target, so a
  provider that moves without its row fails the unit suite, not a proof.
- **The note is quiet.** It appears in a gate's diagnostics, which the executed proof records and
  the progress stream prints, and in no top-level gap. An adopter who never reads diagnostics
  learns of the legacy name from the changelog, and from the refusal once the name is removed.
