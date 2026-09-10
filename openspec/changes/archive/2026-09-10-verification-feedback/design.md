## Context

The latest frozen archive proof passed 35 gates in 1158.07 seconds. Its 2838
collected tests took 930.563 seconds, including 887.485 seconds in the land
module. Scope scheduling imposes a module-sized critical path. This is a
measured bottleneck, not proof that worker count should increase.

## Decisions

Use the existing pytest scheduler rather than implement another executor.
Keep worker, timeout, sharding and coverage controls unchanged. Native work
stealing permits independent test items to move between workers. Verify the
same collected identities and verdicts before reporting any speedup; separate
fixture cost and concurrent-host noise from scheduler behavior.

Keep JUnit and coverage as test-owned artifacts. The hosted wrapper only
projects their observations; it does not create another proof authority.
GitLab consumes native JUnit and Cobertura reports. GitHub uses its native
job-summary file and the existing artifact-upload action, with no extra token
permissions. Artifacts remain available after test failure. Missing or malformed
reports are visible, never interpreted as zero tests or passing coverage.

Broader improvements remain in the existing terminal plan: complete action
input closure, safe evidence reuse, readiness-driven DAG scheduling, fixture
boundary reduction, and typed extension contracts. This Change does not
implement a general orchestration platform or relax exact-current proof.

## Risks And Verification

Work stealing may repeat broader fixtures and reveal order dependencies. Keep
the prior workload identity and compare actual runs rather than predict a
percentage. Reports are observations, not authorization; missing reporting may
not hide a failed proof. Preserve exact exit codes and source binding.

Exercise passing, failing, missing and malformed reports, both Forge templates,
serial and parallel test settings. Run focused tests and cheap static checks
before a frozen full proof. Report remote visibility only after target readback.
