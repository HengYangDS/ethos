# Tasks

## 1. Algebra and proof path

- [x] 1.1 Add the kernel `Outcome` with `of`, `part` and `combine`, `OutcomeError` and `outcome_of`,
      and make `ProcessExecutionError` an `OutcomeError`. Done when kernel tests show the reduction
      order, the class-code-first union, the five-code bound with its omitted count, a declared
      verdict surviving an exception, and the leading gap as the message, and when a mutation of
      `combine` fails them. The 5 kernel tests pass at `e3686225a`; deriving `combine`'s verdict
      from the gaps fails one of them.
- [x] 1.2 Carry each failed gate's causes through `prove --execute`. Done when tests show three
      things: a timed-out gate reaches the top level as `gate_unknown:<gate>` and then
      `gate_timeout:<gate>`, with verdict `unknown`, a bounded diagnostic and the timeout remedy;
      the dry-run output is unchanged; and the stored statement fields are unchanged.
      `test_proof_causes` and the prove command test pass at `e3686225a`, the dry run equals the
      empty outcome, and the 497 proof, kernel and execution source tests, statement binding
      included, pass; dropping the causes or forcing `block` fails all three proof-path tests.

## 2. Boundaries

- [x] 2.1 Build the process, public-contract and Git-effect failure results from the carried
      `Outcome` through `EthosResult.from_outcome`. Done when tests show every carried gap and the
      producer's verdict class at each boundary, with the exact matchers unchanged.
      `test_outcome_boundaries` shows every carried gap and the declared class at the process and
      public-contract boundaries, and the stale-base and admission matchers keep their tests, at
      `e3686225a`; the 130 Git effect and compensation tests pass at `eb818fed4`.

## 3. Aggregators

- [x] 3.1 Give a dependent of an unknown prerequisite `unknown`, and keep `prove --host`'s causes.
      Done when runner tests show both. The runner parametrization keeps an unknown prerequisite's
      dependent `unknown`, the host observation test keeps `gate_timeout:tests` after
      `gate_unknown:tests` with verdict `unknown`, and both pass at `46488f371`; forcing `block`
      fails the first.
- [x] 3.2 Reduce status, Work Lane refresh, retirement and commit creation through `combine`, and
      carry every gap through the failure helpers. Done when one regression per aggregator shows a
      part's specific gap and verdict class at the top. `test_outcome_aggregators` covers status,
      refresh and retirement, and `test_creation` covers commit creation, at `46488f371`; the four
      updated retirement suites pass at `a0909187e`.
- [x] 3.3 Rename the undeclared-result gap to `gate_undeclared:<gate>`. Done when the gate policy
      and the hosted verification receipt use it. The hosted receipt test pins
      `gate_undeclared:undeclared` and passes at `46488f371`.

## 4. Ratchet, specification and notes

- [x] 4.1 Refuse single-gap transport in product code with an architecture test. Done when it passes
      on the lane and fails on a planted `raise ValueError(gaps[0])`. It passes at `6fb686bac`, and
      a `raise ValueError(gaps[0])` planted in `contracts/plan.py` fails it.
- [x] 4.2 Write the `kernel` and `quality` deltas. Done when strict validation and the cumulative
      archive simulation pass. Strict validation passes, and the archive simulation finds 12 of 12
      specifications valid at `711ac462f`.
- [x] 4.3 Name the change in the Unreleased notes. Done when the changelog validates. The 139
      release tests pass at `a0909187e`.
