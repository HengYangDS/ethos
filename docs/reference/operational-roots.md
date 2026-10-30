---
subject: ethos:operational-roots
role: reference
state: active
relations:
  projects: ../governance/product-design-contract.md#first-hour-ux
---

# Operational Roots

This reference projects the hidden operational roots `ethos lane` and `ethos hook` from the
[Product Design Contract](../governance/product-design-contract.md#first-hour-ux), where they
support admission only. The [Command Plane](command-plane.md) lists the public commands.

`ethos lane format` prepares native source postimages without writes. Optional
literal paths select exact inputs; omission selects tracked and non-ignored new
authored source while retaining foreign, generated, immutable and dependency
owners. `--check` evaluates those same postimages. Fixing requires `--apply
--authorize --expect-head <current-head>` and the current Work Lane admission;
it preserves HEAD, index and source modes. Missing inputs remain unknown and
policy or parse conflicts refuse before effect. Native formatter ignores and
pragmas preserve bytes but do not waive independent semantic gates. Nox `format`
and `format_check` project this operation; they do not own another formatter or
replace the complete proof closure.

The hidden operational roots `ethos lane` and `ethos hook` provide admission and guards, not another lifecycle.
Bind the exact checkout and paths before tracked edits:

```bash
ethos lane prewrite <paths> --editor-root <worktree> --require-editor-root --json
```

To close the paradigm gaps whose repair follows from their carriers alone,
preview the repairs, then apply them inside the Work Lane:

```bash
ethos lane repair-paradigm --json
ethos lane repair-paradigm --apply --json
```

The preview names each carrier with its diff, the follow-up commands such as a
peer remote rename, and every gap that needs judgment with its canonical repair.
Apply writes only after exact-path prewrite admission and plans nothing on a
repaired tree. It neither runs the follow-up commands nor commits.

Authoring permission and resource retirement are distinct. An explicitly named
local topic ref may retire after exact accepted absorption even if its name is
not `work/*`. Use `ethos lane retire absorbed-ref --branch <branch> --expect-head
<source-oid> --accepted-head <accepted-oid> --root <accepted-root> --json` for an
unlinked, unleased ref; use `ethos lane retire landed --branch <branch>
--expect-head <source-oid> --root <accepted-root> --json` for a clean linked
worktree. First inspect the dry-run and follow its exact authorized apply
command. Existing retirement receipts own partial-effect recovery.

Neither path grants source writes, deletes repository root resources, discards
dirty work, or closes a remote review. Current Lease and exact-object checks
remain in force, and installed hooks require the admitted retirement intent.

Before retirement, drain every writer under lane coordination, review final
content, then derive and apply its exact receipt. Lease transfer or an empty
process scan does not stop writers. Active consumers, unknown liveness or content
changes block disposal; changed final bytes require re-derivation. This protocol
does not isolate arbitrary uncooperative same-UID filesystem writes.

For a historical topic with explicitly reviewed staged, unstaged, untracked or
ignored residue, use the existing abandonment owner instead of copying a backup:

```bash
ethos lane retire abandon --branch <source-branch> --reason-code absorbed-semantics --reason '<current semantic owners and disposition>' --review-content --root <accepted-root> --json
```

Derivation records the exact literal tree and index; it does not prove semantic
absorption. Inspect the receipt before using its returned authorized command.
Changed content or authority requires fresh review; interrupted disposal uses
the original receipt and checks surviving content before continuing. Unsupported
native observation blocks; this capability does not imply verified Windows
reviewed-content support.

When one clean historical topic is fully retained by another local topic, derive
retirement without treating that history as accepted product semantics:

```bash
ethos lane retire superseded --branch <source-branch> --expect-head <source-oid> --absorbed-by refs/heads/<retained-branch> --reason '<retention reason>' --root <accepted-root> --json
```

This full-ref form creates the existing immutable retirement receipt and returns
one `lane retire recover` command. Inspect that receipt, then follow its exact
`--receipt`, `--receipt-sha256`, and `--authorize --apply` continuation. Direct
`superseded --apply` with a retention ref is rejected: it would otherwise silently
rebind a moved retained OID. Missing or expired target Lease is admissible; a
valid target Lease requires its current holder. Retained ref movement invalidates
the receipt. Re-derive from current facts instead of replaying stale coordinates.
The surviving ref and checkout are not written, and their unique semantics still
need adjudication before final retirement.

For independent maintenance, select a full trusted commit OID without changing
the current candidate train:

```bash
ethos lane start <name> --base <full-commit-oid> --holder-ref "$ETHOS_ACTOR" --root <accepted-root> --json
```

Inspect the planned base and follow its exact apply command. Omission of `--base`
retains the candidate default. Both modes use current repository policy, trust,
runtime and Lease authority; an old source does not reactivate old governance.
Creation asserts the observed candidate and writes only the owned lane ref.
Failure compensates only newly created resources. This creates authoring state,
not release authority; exact proof, integration and publication remain separate.

For a registered Work Lane that has lost its Lease, derive coordination recovery
without recreating its checkout or changing its staged and unstaged content:

```bash
ethos lane lease reacquire --path <worktree> --holder-ref "$ETHOS_ACTOR" --root <accepted-root> --json
```

Inspect the exact coordinates and follow the returned authorized apply command.
That command binds the proposed Lease expiry as well as content; replay recognizes
only the exact four-field relation and reuses its existing effect evidence.
An existing foreign or expired Lease requires its own handoff or takeover path;
reacquisition does not overwrite it. The recovered relation does not grant
OpenSpec acceptance or tracked-write permission: obtain fresh prewrite admission
before editing. A partial result identifies a committed Lease separately from
missing effect evidence, so its continuation does not repeat the insertion.
