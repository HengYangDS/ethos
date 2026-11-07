# Design

## Context

See [proposal.md](proposal.md). The design record is
`build/runtime/work/hardening/post-beta6-hardening-draft.md`, section 3, as amended by its decision
of 09:5x. The test follows the AST idiom of `tests/architecture/test_single_gap_transport.py`: a
whole-tree assertion, plus planted snippets that pin the rule.

## Goals / Non-Goals

Goals:

- A new reader of an ETHOS result cannot land without expanding a bounded result.

Non-goals:

- Readers outside `src/` and `tools/`, such as agent kits.

## Decisions

- **Two triggers.**
  - The first is a JSON parse of stdout (an attribute `.stdout` or a name `stdout`) in a module
    with an argv that holds `ethos.cli`, or both `--root` and `--json`. Two modules whose argvs
    run other tools are declared by name: publication retirement (gh and glab rows) and the first
    Change acceptance (OpenSpec output).
  - The second is any JSON parse whose result is read for `required_gaps`,
    `missing_facts_or_evidence` or `bound`, or tested for a `command` key.
- **Compliance.** A parse complies when it is an argument of an expander, or when the name it is
  assigned to is passed to one in the same function. The expanders are `expand_result` and each
  module-level function that passes one of its parameters to it, such as `_read_result`.
- **One reader path for acceptance.** The MCP acceptance runs the CLI through `invocation.invoke`,
  which expands and validates the current schema. The acceptance's equality with the MCP and SDK
  surfaces then compares full results.
- **Gate verification fails closed.** A bounded ETHOS-shaped gate result is expanded before its
  verdict and gaps are read. A detail that cannot be read makes the gate unknown, with the
  expansion's own gap.

## Risks / Trade-offs

- Data flow is followed only within one function, so a parse handed to another module's helper is
  reported and must be wrapped where it is parsed.
