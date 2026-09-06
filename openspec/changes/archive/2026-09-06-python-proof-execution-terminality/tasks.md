## 1. Pin the semantic failure

- [x] 1.1 Add a focused regression that crashes a real xdist worker and proves
  the existing Python test gate replays the test; observe RED.

## 2. Make worker loss terminal

- [x] 2.1 Add terminal worker-loss behavior at the existing pytest configuration
  owner without retries, timeout growth, alternate distribution, or another
  state machine.
- [x] 2.2 Prove parallel execution runs the crashing test exactly once with a
  concrete worker/test diagnostic.

## 3. Closure

- [x] 3.1 Validate the official Change strictly and prove repository-wide
  references expose one owner for Python test command compilation.
- [x] 3.2 Run focused tests, static checks, and the smallest affected gate; verify
  one terminal worker-loss result.
- [x] 3.3 Keep post-implementation proof, archive, exact-CAS integration,
  runtime readback, publication, and lane retirement in their native receipts
  and Attestations rather than making those later effects active Change tasks.
