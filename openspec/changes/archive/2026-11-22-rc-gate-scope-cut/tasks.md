# Tasks

## 1. The record

- [x] 1.1 Add DR-0035 with the Decision that the five seats signed, copied from the proposal by
      program, and its row in the decisions index. Done when the record's Decision holds the
      proposal's ten items word for word and the decision-record test passes. (By program at
      `684d73f2b`: the record's Decision holds the proposal's 10 items word for word; the 40
      architecture test files pass.)
- [x] 1.2 Mark in DR-0026 and DR-0029 each sentence that DR-0035 adds to or replaces, and declare
      the relation in both. Done when, with the marks and the relation removed, each record's body
      equals the head's word for word. (By program at `684d73f2b`: each record's body equals its
      body at `eee24a887` with this record's marks removed, 2 in DR-0026 and 3 in DR-0029; each
      front matter names DR-0035 under `updated_by`.)

## 2. Lane only

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Full pre-check and readiness ran as ticket r4c4 at acf0b50ef (queued 11:34:13, admitted
      11:54:09, released 12:14:26): precheck passed, 0 findings, stamp for tree
      018f0d614ee7db2af1343c7d9acbbdd6c67ddcd3; readiness exit=0, 28 gates passing, 6 not run, 0
      failing.
