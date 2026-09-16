## Cause And Boundary

The bootstrap script conditionally invokes the existing trust-binding owner
when the operator declares a trust anchor. The platform fixture copies every
ambient environment variable but provides a deliberately narrow fake Python.
Its result therefore changes with the caller's signing configuration. Removing
the production branch or clearing the runner's real trust anchor would weaken
the product and is not the repair.

## Design

Keep the fixture's external package-manager commands controlled. Supply its
environment explicitly. An unrelated ambient trust anchor is not a fixture
input; an explicitly selected test anchor is. For the declared-anchor case,
execute the actual Python trust-binding code and native Git against the
disposable repository. Verify the resulting local Git setting and unchanged
anchor bytes. Existing owner tests continue to reject missing, unprotected and
repository-controlled anchors.

## Verification And Order

First reproduce the hosted failure with the ambient anchor set. Repair only the
fixture boundary, then run the platform/anchor matrix and existing trust-owner
regressions. Use focused and static checks before a new exact full proof. Accept,
install and publish through existing public commands; hosted success requires a
separate exact-ref observation. No test, package or credential authority is
inherited merely because it exists on the runner.
