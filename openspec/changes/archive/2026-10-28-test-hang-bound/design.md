# Design

## Context

See [proposal.md](proposal.md). `.config/checks/pytest/pytest.toml` has declared `timeout = "120"` since `5075ebe8a` (2026-09-20). It sets no `timeout_method`, so pytest-timeout uses signals on POSIX and a thread on Windows. The test gate in `tools/ci/python_test_gate.py` runs `min(12, cpu_count)` xdist workers with `--maxfail=1`. `tools/ci/python_test_order.py` starts the tests with the longest recorded durations first.

The eight heaviest recorded tests were measured on 2026-10-28 at `550ad4c7f`. "Alone" means one at a time, at an ambient load of 10–12. "12 workers" means the 24 heaviest tests together on 12 workers, with no other gate running. "Full proof" is the second `stable-check-names` proof.

| Test                                                                                    | Alone  | 12 workers | Full proof       |
| --------------------------------------------------------------------------------------- | ------ | ---------- | ---------------- |
| `test_process_intent_carries_product_work_through_native_integration`                   | 50.9 s | 79.9 s     | 122.5 s          |
| `test_public_maintenance_release_preserves_shared_trains[independent]`                  | 41.3 s | 76.8 s     | 103.1 s          |
| `test_public_maintenance_release_preserves_shared_trains[accepted_ff]`                  | 40.4 s | 82.2 s     | 109.1 s          |
| `test_peer_that_missed_a_release_receives_the_attested_tag`                             | 37.9 s | 66.3 s     | 94.0 s           |
| `test_source_and_release_builds_preserve_exact_metadata`                                | 35.7 s | 54.6 s     | stopped at 120 s |
| `test_identity_transition_is_explicit_and_target_scoped[branch]`                        | 33.6 s | 51.0 s     | 104.0 s          |
| `test_stdio_discovery_adoption_and_reconnect`                                           | 33.1 s | 54.3 s     | 95.6 s           |
| `test_public_release_preserves_native_package_and_signed_tag[accepted_ff-sha1-VERSION]` | 32.3 s | 51.5 s     | 96.9 s           |

Of the 7,779 recorded tests, 90 take 30 s or more, and together they account for 5,029 s of the 16,184 s total.

## Goals / Non-Goals

**Goals:**

- A healthy test never fails a proof because the host is busy within the admitted load.
- A test that hangs still fails within a fixed bound and reports its stack.
- One declaration owns the per-test bound.

**Non-Goals:**

- Making the heavy tests cheaper. Their time is mostly Git and OpenSpec subprocesses.
- Changing the order, the worker count, `cpu_reservation` or proof admission.

## Decisions

### 1. The bound detects hangs, not slowness

A hang guard belongs where no healthy run reaches. In a full proof, the heaviest tests ran 2.4–3.4 times as long as alone, and between a fifth and three fifths of that growth already appeared on 12 workers with no other gate running. Load can also rise after admission: during `surface-pruning`'s first proof it reached about 31. At 600 s, the bound stays about 5 times above the slowest full-proof observation (122.5 s) and about 12 times above the slowest test run alone (51 s). A hang still fails within 10 minutes, well inside the length of the unit gate.

### 2. A test may only tighten the bound

Raising the bound one test at a time hides the shared cause and grows into a list. The three 240 s marks go away. Under the new bound, each of them would only tighten the limit for one of the heaviest tests and bring back the false failure. A test keeps a mark only to time one fast operation: alias expansion in the Markdown link check (2 s), native command input and environment (5 s), and output capture through regular files (30 s). An architecture regression parses every test module and requires each literal `pytest.mark.timeout` to stay below the declared bound. A mark whose value is not a literal counts as raising it.

### 3. The native mechanism stays

pytest-timeout and its default method stay. The bound is still one value in `pytest.toml`, and `ETHOS_TEST_TIMEOUT_SECONDS` keeps overriding it for one explicit run, as before.

## Risks / Trade-offs

- [A real hang takes longer to fail] → It fails in 10 minutes, not 2. `--maxfail=1` stops the run at the first timeout, and the stack is printed.
- [Slow tests grow unnoticed] → The gate prints the 20 slowest tests on every run, and the duration record keeps them. Test cost is reduced where it arises, in the separate throughput work.
