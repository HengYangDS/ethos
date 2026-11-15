# Design

## Context

See the [proposal](proposal.md). The provider catalog gives each gate provider an ID and keeps the
`ethos.<module>:<callable>` name that declarations used before it resolving for one support
window, so one provider has two valid names. The gate contract's check for a repeated provider is
older than the catalog and compares text. The provider seam runs each reference it is given and
records each report under the declared name, and the source-integrity join accepts exactly one
report from the integrity provider under any of its names.

The catalog's own Change, `provider-ids`, ruled that a declaration checks a reference's form and
that the readers resolve it, so that a registry is not valid under one release and invalid under
another.

The schema validation gate checks the projection of each packaged gate against the gate schema,
after the gate model has validated the declaration. The schema's `verification_providers` property
has accepted any string, repeated or not, since before the catalog.

The gap registry reads its packaged table once and caches it. Its readers today are its own repair
lookup, the static registry test and the shared CLI test runner. No product module imports the
registry yet, and none of the readers changes a row.

## Goals / Non-Goals

Goals:

- A declaration that names one provider twice is refused where a repeated text already is.
- The schema holds a verification provider to the form and the unique items of a provider.
- A reader cannot change the registry through a row it received.

Non-Goals:

- A new gap code or a new message for the repeated provider: the refusal keeps the contract's
  existing message.
- Running a repeated provider once, or accepting two reports in the integrity join.
- Any change to how a family prefix registers a code: `gap-code-literals` owns it.
- Removing a legacy name or narrowing the reference form.

## Decisions

1. **The gate contract compares provider references by the provider each names.**
   - **Rests on:** the two new cases of `test_gate_executor_malformed_shapes_fail_closed`, which
     the contract accepted at the head before this Change; two probes, kept with the Change's
     preparation outside this repository, in which the policy functions bind both names into the
     gate's execution identity without a gap, the provider seam calls one provider twice and the
     integrity join answers two passing reports with `source_integrity_unproven:<member>`; and the
     shared-gate composition, which already compares providers under their catalog IDs.
   - **Considered:** a gap from the policy compiler beside `gate_provider_unresolved`, which would
     name the gate and the provider, but needs a new gap code and a second place that judges a
     repeated provider, and refuses only a proof that selects the gate; running each provider once
     at the provider seam, which hides a declaration error and leaves a declared name without its
     report, which the quality join requires for each name; and a refusal in the integrity join,
     which covers one provider and lets any other repeated provider run twice.
   - **Chosen because:** the contract already owns the rule that a gate names a provider once, and
     only its comparison predates the second name. The comparison asks the catalog which ID a
     reference names and compares a name that the catalog lacks as its text, so it never decides
     whether a name resolves. Two trade-offs are accepted: the refusal keeps the message
     `gate executor invalid` and does not name the provider, and the contract now reads the
     catalog, which `provider-ids` kept out of it (see Risks).
   - **Applies to:** the providers and the verification providers of every gate that the model
     validates: the packaged registry, a declared registry and a profile's own gates. The two
     lists are compared separately, since a gate holds entries in one of them only. An unresolved
     name is not judged here; the policy compiler still refuses it.
2. **The schema repeats the reference form for a verification provider, and a test holds the two
   statements equal.**
   - **Rests on:** the two refusal cases of
     `test_gate_schema_holds_a_verifier_reference_as_the_model_does`, which the schema passed at
     the head before this Change; the schema of the last release, where the property is as
     unconstrained; and the schema gate's instance check, which reads gates that the model has
     already validated.
   - **Considered:** one definition under `$defs` that both lists refer to, which cannot drift but
     rewrites the `providers` property as well, a refactor beyond the defect; and deriving the
     property from the model, whose rule is a validator that its JSON Schema projection does not
     carry.
   - **Chosen because:** it is one hunk that leaves the `providers` property untouched, and the
     file states its other repeated fragments inline. The cost is a second copy of the pattern;
     the regression compares the two `items` statements, so a change to one copy alone fails.
   - **Applies to:** the form and the textual uniqueness of both lists. Identity through the
     catalog stays with the model: a JSON Schema cannot read the catalog, so an ID with its legacy
     name passes the schema and the model refuses it.
3. **A registry reader receives a copy of a row.**
   - **Rests on:** `test_a_row_handed_to_a_reader_is_its_own_copy`, which fails at the head before
     this Change; the readers listed under Context; and the table itself, where every value of a
     row is a string today, so a copy of a row shares nothing that can change.
   - **Considered:** freezing each row at load behind a read-only mapping, which changes the
     declared row type for every reader; and leaving the row shared because no reader changes one
     today, which lets the first reader that fills in a default corrupt every later read without
     a failure.
   - **Chosen because:** it is three lines and no type changes. The cost is one small copy for
     each row read.
   - **Applies to:** the two readers that return rows. The reader of the family prefixes already
     returned a copy of a mapping of strings.
4. **The family prefixes stay, and the measurement goes to a draft Change.**
   - **Rests on:** three walks of the syntax tree of every module under `src/ethos` and a reading
     of each value literal at its sites, kept with the Change's preparation outside this
     repository. With the site rules of `tests/architecture/test_gap_registry.py`, 29 sites are
     registered only through a family: 13 whole literals of 12 codes, 2 f-strings that hold a
     complete code, and 14 f-strings whose head is exactly a family prefix. Over every string
     literal, 183 texts with a family prefix have no row and 142 of them are used as values. Read
     at their sites, 92 of the 142 are gap codes, and 80 of the 92 stand at no position that the
     static test reads.
   - **Considered:** rows for every whole literal now, which needs an owner package for 92 codes
     and for up to 17 more that f-strings hold; and the static half alone, 14 rows and a row rule
     for a whole literal in the static test, which closes the positions that the static test reads
     and leaves the runner's check as it is, because a code met at run time does not show how it
     was built.
   - **Chosen because:** registration through a family prefix is the kernel's stated requirement,
     so narrowing it is a design change with its own delta; and 92 rows with their owners are more
     than a defect repair before a release holds.
   - **Applies to:** the registration of a code. The draft `gap-code-literals` carries the counts,
     the two halves and the next action.

## Risks / Trade-offs

- A registry or a profile that names one provider under both names is refused where it was
  accepted, as `gate_registry_invalid:<path>` or `repository_profile_invalid:<path>`. No released
  build accepts a catalog ID, so such a declaration can exist only on an unreleased head.
- The contract's answer now depends on the catalog of the release that reads the declaration, in
  one case: an ID beside a legacy name. A release that maps the legacy name to that ID refuses the
  declaration. A release that no longer maps it accepts the declaration and refuses a proof of
  that gate, because the name is unresolved. No release runs the gate.
- The refusal names the declaration and not the repeated provider. A reader finds the gate by
  reading the declaration.
- The model accepts an `ethos.` name with an empty module part and the schema does not. That held
  for a provider, and it now holds for a verification provider too. No catalog entry has that
  form, so such a name refuses the proof as unresolved in either list. This Change does not move
  the model's form.
- Until `gap-code-literals` lands, a new whole literal under a family prefix still passes both
  checks without a row.
