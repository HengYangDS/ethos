# Tasks

## 1. Test isolation

- [x] 1.1 Remove the inherited admission variables in the suite's hermetic environment. Done when
      the gates and host run tests fail with `ETHOS_HOST_ADMISSION` and `ETHOS_HOST_CPU_CAP` set
      before the change and pass after it, and pass without them. With both set, 1 of 159 failed
      before and 165 of 165 pass after; the 1,611 architecture, policy and repository tests pass.
