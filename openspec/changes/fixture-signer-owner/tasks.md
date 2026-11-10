# Tasks

## 1. One signer owner and one session build

- [ ] 1.1 Move every signer to `configure_fixture_signer` and delete the other two. Done when no
      test support creates a signer elsewhere, `/usr/bin/ssh-keygen` appears only as a mocked
      value, and the touched tests pass.
- [ ] 1.2 Resolve the invoking build once per worker. Done when fixture runtime installs resolve
      it at most once per worker and an `ethos` profile root keeps its own branch.

## 2. Acceptance

- [ ] 2.1 Pass the precheck, the impacted sweep and readiness at the lane head. Done when each
      passes on the committed head.
