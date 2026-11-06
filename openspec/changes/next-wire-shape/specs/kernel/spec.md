## MODIFIED Requirements

### Requirement: Kernel Result Contract

ETHOS SHALL emit schema-version-`3` JSON result envelopes with `verdict`, `state`, `summary`,
`diagnostics`, `required_gaps`, singular `next_action`, `user_decision_required`, and `data`.
`continuation`, `next` and `missing_facts_or_evidence` are derived fields, not lifecycle state.
`summary.runtime` names the product that produced the result.

#### Scenario: Automation reads command output

- **WHEN** an automation consumer requests JSON output from an ETHOS command
- **THEN** the response is one parseable schema-version-`3` object with the stable result fields
- **AND** it preserves `state` and `required_gaps`, has no plural action field, and derives exactly
  one `continuation` value
- **AND** `missing_facts_or_evidence` equals `required_gaps` only for an `unknown` verdict
- **AND** every reader re-derives `next` from `next_action` and `continuation`; a carried `next` must
  be well formed in this vocabulary and is never trusted, so another runtime's payload of the same
  schema stays readable unless its carried `next` uses a value this vocabulary does not name
- **AND** only a bounded result carries `bound`, which names the full result's detail artifact and
  what the bound left out

#### Scenario: A version-2 payload is refused

- **WHEN** a reader validates a schema-version-`2` payload
- **THEN** it refuses the payload instead of reading it as version 3
