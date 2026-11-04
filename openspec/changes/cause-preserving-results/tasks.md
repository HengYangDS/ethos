# Tasks

## 1. Algebra and proof path

- [ ] 1.1 Add the kernel `Outcome` with `of`, `part` and `combine`, `OutcomeError` and
      `outcome_of`, and make `ProcessExecutionError` an `OutcomeError`. Done when kernel tests show
      the reduction order, the class-code-first union, the five-code bound with its omitted count,
      a declared verdict surviving an exception, and the leading gap as the message, and when a
      mutation of `combine` fails them.
- [ ] 1.2 Carry each failed gate's causes through `prove --execute`. Done when tests show three
      things: a timed-out gate reaches the top level as `gate_unknown:<gate>` and then
      `gate_timeout:<gate>`, with verdict `unknown`, a bounded diagnostic and the timeout remedy;
      the dry-run output is unchanged; and the stored statement fields are unchanged.

## 2. Boundaries

- [ ] 2.1 Build the process, public-contract and Git-effect failure results from the carried
      `Outcome` through `EthosResult.from_outcome`. Done when tests show every carried gap and the
      producer's verdict class at each boundary, with the exact matchers unchanged.

## 3. Aggregators

- [ ] 3.1 Give a dependent of an unknown prerequisite `unknown`, and keep `prove --host`'s causes.
      Done when runner tests show both.
- [ ] 3.2 Reduce status, Work Lane refresh, retirement and commit creation through `combine`, and
      carry every gap through the failure helpers. Done when one regression per aggregator shows a
      part's specific gap and verdict class at the top.
- [ ] 3.3 Rename the undeclared-result gap to `gate_undeclared:<gate>`. Done when the gate policy
      and the hosted verification receipt use it.

## 4. Ratchet, specification and notes

- [ ] 4.1 Refuse single-gap transport in product code with an architecture test. Done when it
      passes on the lane and fails on a planted `raise ValueError(gaps[0])`.
- [ ] 4.2 Write the `kernel` and `quality` deltas. Done when strict validation and the cumulative
      archive simulation pass.
- [ ] 4.3 Name the change in the Unreleased notes. Done when the changelog validates.
