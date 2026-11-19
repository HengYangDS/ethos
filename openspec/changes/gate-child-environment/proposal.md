# Proposal

## Why

The archived `rc-plan` design orders the row in its Family 4 (lines 101 to 104): "`gate-environment`
(working name; R8(c); unsized) follows A7 and precedes A10 and MCP `prove`: proof gates run in an
allow-listed environment without SSH agent or forge tokens, or the PDC states the non-sandbox
boundary, and one owner redacts persisted failure output." The Change `gate-environment` is the
first slice of that row, in 0.2.0-beta.13: an executed proof reports what its declared commands
inherited, and no child's environment changes. This Change is the second slice, the environment
itself. Run handles (A10) and MCP `prove` wait for it, as the same lines order. In 0.2.0 the runner
of a detached run starts in the launch environment, and its list follows with this state.

The owner decided the form on 2026-11-17: a declared command's child is built from a list, by a
state that each repository declares, and the default state reports and changes no child. The
committee's resolution of the same day, which the owner approved, places it: the state ships in the
first release after 0.2.0 and becomes the default one release later.

The design of `gate-environment` (Decisions 4 and 6) measured what the build changes, on
2026-11-17 at its base:

- A declared command's child receives every variable of its launch today, 156 of 156 in one
  measurement, with an SSH agent socket and every class of token among them. A child that was
  started with the list of kept names, the locked toolchain's environment and one named variable
  received 20 of 144 names and none of the credential markers; the named variable arrived.
  Building it took 0.21 seconds.
- A tool that the lock does not hold was absent from that child's path. So a command whose first
  word is such a tool ends as `missing_command`, and a gate that needs a variable which it does
  not name loses it. One governed repository's gate needs the path of a browser that its hosted
  job declares as a variable.
- Of the 32 command gates that 8 profiles on the preparing host declare, 26 start with a bare
  tool name that the launch path resolves, and none of the 81 gate declarations in that host's 30
  checkouts names a variable.
- The releasing host launches every proof from an empty environment with a home directory, a
  system path and a temporary directory, by scripts outside the product.
- Three launches in three days gave a wrong result for this cause, as the session that keeps
  the governed repositories reported on 2026-11-19: its own cell on 2026-11-16; the copies run
  of 2026-11-18, where one repository's declared command met the host's npm 11.20.0 in place of
  its declared 12.2.2 and another's proof timed out; and a launchd helper the same evening.

## What Changes

Decided by the owner:

- Each repository declares the state of its gate children. The default state reports and changes
  no child. Under the other state a declared command's child is built from a list, and the
  repository names the variables that its gates need.
- The state ships in the first release after 0.2.0 and becomes the default one release later.

Designed here, around that decision:

- The profile carries the state: `report` or `allow-listed`.
- Under `allow-listed`, a declared command's child receives the product's list of kept names,
  the locked toolchain's environment with a path of the locked tools and the host's own command
  directories, and the variables that its gate names. It receives no Git configuration overlay
  and no `VIRTUAL_ENV`, and its standard input is closed, as appendix A.7 of the plan asks for
  children other than local Git.
- `summary.environment.mode` states the state that ran, and a result names each variable that a
  gate declared and the launch did not hold.

Candidates for this row's design, none decided:

- Where a gate names its variables, and how a runtime that does not read that field meets a
  profile that uses it: the gate model refuses unknown fields today, so the reader ships before
  the first profile that declares one.
- Whether a provider's children are built from the same list.
- Whether the proof Attestation records the state and the report, which changes its schema.
- The product builds the launch that host scripts keep today, so that a proof launched from any
  shell and one launched from an empty environment judge the same subject.
- The list that the release journey's tools keep converges on the product's list.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The gate runner, the gate model, the profile, the owner module of a gate child's environment and
the requirement `Locked execution keeps native mise policy`. Each repository that declares
`allow-listed` names the variables its gates need and locks the tools its commands name.

Owner: the release lead; the form is the owner's decision of 2026-11-17. Next action: design the
declaration and its reader release, with the sixth measured case as the acceptance of a named
variable. Read again: when the first release after 0.2.0 is planned.
