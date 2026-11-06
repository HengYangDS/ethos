# Tasks

## 1. Resolver

- [x] 1.1 Specify the resolver with failing tests: a local key, an invalid key, `http` and `https`
      remotes with port and `.git`, `insteadOf`, a refused credentialed URL that is not echoed, and
      an unresolved SSH or scp-like remote with its follow-up. Done when they fail on `_forge_url`.
      Red at 21:44: 16 failed, and the new module was missing.
- [x] 1.2 Replace `_forge_url` with `forge_web_repository`. Done when those tests and the retirement
      review tests pass. Green at 21:46: 38 passed; Ruff and Ty pass.

## 2. Retired fields

- [x] 2.1 Specify with failing tests that the loader refuses each retired field, an absent
      `[publication]` table is zero peers, the paradigm obligation reports each field and blocks
      only prove, land and publish, the repair is pure, idempotent and value-free, and adopters
      without the commands pass the executable-reference check. Done when they fail on the current
      loader and paradigm. Red at 21:58:33: 10 failed.
- [x] 2.2 Retire the fields in the loader, the paradigm and the repair, and in `declarations.py`;
      repair ETHOS's own `release.toml`. Done when those tests and the publication and paradigm
      tests pass. Green at 22:01:18: 59 passed. ETHOS's own `lane repair-paradigm --apply` repaired
      its `release.toml` at 22:15:39.

## 3. Fallback

- [x] 3.1 Specify with failing tests that `local_ci_fallback` projects every proof-admission state
      with text, that the prove continuation carries `--full`, and that a refused publish names the
      repair on the readiness and `--ref` paths. Done when they fail. Red at 22:20:48: 2 failed and
      1 import error.
- [x] 3.2 Rebind the fallback, add `--full`, prefer the repair, and retire `local_ci`. Done when
      those tests and the inspection tests pass. Green at 22:42:11: 22 readiness tests pass, after
      the transport admission tests passed at 22:40:49.

## 4. Rollback

- [x] 4.1 Specify with failing tests that a selector-only rollback across a repaired declaration
      refuses with `runtime_rollback_declaration_repaired`, leaves no effect, and passes once the
      lane restores the predecessor's declaration. Done when they fail. Red at 22:47:06: 2 import
      errors.
- [x] 4.2 Add the activation preflight and the status guidance. Done when those tests and the
      runtime-activation tests pass. Green at 22:48:30: 22 passed; 878 hook and runtime tests at
      22:50:53, and 294 with the status guidance at 23:19:01.
- [x] 4.3 Read the target's publish result through `expand_result`, because a bound can shorten
      `required_gaps`. Done when a bounded result whose detail alone names the repaired-declaration
      gap refuses with `runtime_rollback_declaration_repaired`. Red at 05:49:25: the preflight
      admitted a bounded answer whose detail alone named the repaired declaration. Green at
      05:50:25: 22 rollback and preflight tests pass.

## 5. Acceptance

- [x] 5.1 Keep the old fields only in the retained predecessor fixture and repair in the lane; state
      the rollback limit in the upgrade receipt. Done when the acceptance tests pass. At 00:16:00:
      222 delivery and architecture tests pass. The full sweep ending 00:08:24 passed 8,165; of its
      3 failures, two were fixed at 00:16 and the third, the mise trust test, is fixed on dev.
- [ ] 5.2 Run the both-runtime checks and compare the plans before landing. Done when each check has
      its receipt.
