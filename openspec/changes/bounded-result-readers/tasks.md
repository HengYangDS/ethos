# Tasks

## 1. Readers of another process's result

- [x] 1.1 Specify the failures with tests. One test shows that the predecessor probe reads the gaps
      of a bounded result from its detail. One shows that the candidate reader refuses a bounded
      result whose detail it cannot read. One shows that `expand_result` returns a full result that
      its model would refuse. Done when the three fail on the current code. Red at 04:33:02: all
      three failed. The result model refused a field that another build adds, the probe returned
      `predecessor_policy_probe_invalid`, and the candidate reader passed a bound it could not read.
- [x] 1.2 Expand in both readers, and have `expand_result` return the producer's mapping. Done when
      those tests and the result, proof admission and hook execution tests pass. Green at 04:35:09:
      128 tests pass in the changed files and the hosted and reference-transaction readers. At
      04:49:52 the 61 test files that read expanded CLI results pass with 1,281.
- [x] 1.3 State the reader rule in the command-plane reference. Done when
      `docs/reference/command-plane.md` names it and the Markdown checks pass. The reference states
      it at `docs/reference/command-plane.md:407-414`; the Markdown checks run at commit.
