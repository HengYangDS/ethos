# Design

## Context

See [proposal.md](proposal.md) and the reviewed design
`build/runtime/work/operator-verbs/cli-product-design.md`, sections 3 and 8.

- `EthosResult` in `src/ethos/result.py` is schema version 2, with a free-text `next_action` and a
  derived `continuation`.
- `apply_payload_budget` externalizes the whole result for `status` and `plan` only. It raises if
  the reduced result still exceeds the budget.
- `emit` in `src/ethos/surface/cli/output.py` applies the budget only when a command passes an
  artifact root.

## Goals / Non-Goals

Goals:

- An agent acts on any command's default result without a second read, and without parsing text
  to learn the effect or authority of the next step.
- No result can grow past its budget, and none can fail to render because of its size.

Non-goals:

- A new reader command. Detail stays in the existing digest-bound artifact. The command-plane rule
  "no alternate reader command" stands.
- A generic "run next" verb. It would let `--apply --authorize` slip past a harness's permission
  rules.

## Decisions

- **One budget rule for every command.** `PAYLOAD_BUDGETS` becomes a default of 16 KiB with
  per-command overrides. `emit` always applies it, so callers no longer opt in, and writes detail
  under the ETHOS store of the repository the command resolved, never under the caller's working
  directory.
- **What stays inline.** Bounding keeps the wire fields, reduces `data`, and adds a top-level
  `bound`:
  - `data` keeps the command's own entries of at most 1 KiB, such as receipts, paths, digests and
    evidence references, because the next call binds to them; a larger mapping keeps its scalar
    fields, so a land result still names `candidate_update.state`;
  - `bound` holds the budget and full size, `detail` (the digest-bound artifact of the full
    result), each failing check's id, exit code and first 20 output lines, the entries shortened
    (`partial`) or moved (`moved`), and the omitted counts.

  The bound lives beside `data`, never inside it, because commands already use keys such as
  `detail` (`adopt`) and `artifact_reference` (`prove`) for their own facts.

  If that is still too large, the failing steps, then the largest kept entries, then the gaps are
  truncated, with counts, never raising. Detail is a convenience copy of a result, not a receipt: it
  lives at `payloads/<command-with-hyphens>/<digest>.json`, a path an agent passes unquoted, and
  detail older than seven days is removed whenever new detail is written, until the store retention
  design (register row 27) owns the policy. Detail is a cache, not an effect, so a reader that
  writes it still only reads; a store that refuses it leaves the result inline, with the reason in
  `bound.detail_unavailable`.

- **`next` derives from the rendered argv, by one owner.** Every command already renders its next
  step as `next_action`, built from an argv with `shlex.join`. `next` is a derived field: when
  `next_action` is exactly one ETHOS argv (a lossless split and join, with no `<placeholder>`),
  `next` carries that argv, its effects from the admission classification in
  `contracts/admission.py`, and the values its flags bind. Anything else is an `instruction` with
  no argv, and a result that needs a person is a `decision`. No producer changes, and the text and
  the data cannot disagree. The command catalog slice replaces the path tables with declared
  per-command effects and lets producers return argv directly.
- **Runtime identity.** `emit` places the committed build identity in `summary.runtime`: product
  version, distribution version and source commit, read once per invocation. The committed identity
  costs about 13 ms; adding the dirty overlay costs about 200 ms in a checkout, so it is left to
  `ethos version`.
- **Schema 3.** `schema_version` becomes `Literal[3]`, and `from_payload` refuses version 2 with
  `result_schema_version_unsupported:2`. `ethos.result.expand_result` is the one reader of a
  bounded result; the test runner delegates to it. The release tooling reads its own schema in full
  and a predecessor release's result as written, because an upgrade journey runs the previous
  release, and only its verdict and data are read.

## Risks / Trade-offs

- `next` relies on producers rendering exact argv. Mitigation: prose and templates stay
  instructions, and the test runner parses every structured next step with the live CLI, so a
  misread step fails the test that produced it. The command catalog removes the rendering step.
- `next` is derived from ETHOS's own rendering, which the continuation requirement now permits
  explicitly; authority boundaries (`user_decision_required`, `continuation`) remain explicit facts.
  Each reader re-derives `next` and checks a carried one only for shape, so a classification that
  changes between runtimes cannot make an older payload of the same schema unreadable. The
  `command-forms` slice makes `next` a wire field set by producers.
- The test runner returns the full result by default, because each new result field moves some
  results across the budget; tests that verify the bound itself ask for `full_payload=False`.
- Some tests read the whole `data`. They read it through `full_result`, `full_payload=True` or
  `result_data`, which delegate to `expand_result`.
- MCP tools still return unbounded results without `next`; the command catalog slice moves them
  onto this contract.
