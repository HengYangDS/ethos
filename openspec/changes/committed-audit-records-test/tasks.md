# Tasks

## 1. The test

- [x] 1.1 Add `tests/unit/ci/dependency_audit/test_committed_records.py` with its two tests and
      move the test of the lock digest out of `test_acceptance.py` into the first of them. Done
      when both pass at the lane's head; each of four stale records (another version, another
      integrity, another lock digest, a node that the lock does not hold) fails the module in a
      scratch copy of that head; Ruff, the format check and Ty accept it; and the source budget
      stays within its ceiling.
      (At `24cc81a6d`: the module and `test_acceptance.py` pass together, 55 cases. With that head's
      policy and module in a scratch tree whose lock, decision module and support module are the
      same bytes, the control passes and each of the four stale records fails the module. Ruff, the
      format check and Ty accept it; the tests read 109,497 of 110,000.)
