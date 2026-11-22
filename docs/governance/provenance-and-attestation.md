---
subject: ethos:provenance
role: explanation
state: canonical
relations:
  canonical_for: evidence attestation
---

# Provenance And Attestation

ETHOS evidence is designed to project into SLSA-style provenance and
Sigstore-compatible signing flows.

The terminal kernel durably persists Attestations. Commitment is compiled from
one exact official OpenSpec projection; Facts are freshly observed and
TransitionPlan is transient. Historical views are derived from Git, official
OpenSpec archives, and Attestations. Governance adapters may sign
Attestations, publish transparency records, or emit hosted CI artifacts, but
adapter output never replaces the repository evidence chain.

`ethos prove --execute --full --expect-head <HEAD> --json` emits a proof Attestation bound to the
compiled Commitment identity, exact HEAD, Facts digest, TransitionPlan digest, policy
digest, effect digest, and verifier boundary. It does not establish a release.
The canonical record is selected through `refs/ethos/attestations-set`; local
command output is a projection, not a second proof selector. What such proof can claim belongs
to the Product Design Contract's
[Evidence Planes And Completion Claims](product-design-contract.md#evidence-planes-and-completion-claims).

## Release Artifacts

Each release run attests every archive and wheel it publishes, and the `SHA256SUMS` file that lists
them, with a GitHub artifact attestation, Sigstore-signed build provenance of that workflow run,
before it creates the release. Release provenance states where a file was built. It is a hosted
provider statement, not an ETHOS Attestation, and neither stands in for the other.

What a published file can be verified against is its release's class. The release pin module of
the product source holds the class of every release as data:

- `attested-main`: the release run was dispatched from `main`, as every attested release so far.
  Its attestation names the release workflow, the ref `refs/heads/main` and the commit that the
  release's signed tag names.
- `attested`: the release run was dispatched from the tag ref. Its attestation names the same
  workflow, the ref `refs/tags/v<version>` and the tag's commit.
- `checksum`: the release has no attestation, or its attestation names another commit than its
  tag. Only the release's `SHA256SUMS` binds its files.

Anyone can check a published archive of an `attested-main` release against all three values:

```bash
gh attestation verify <file> --repo HengYangDS/ethos \
  --signer-workflow HengYangDS/ethos/.github/workflows/ci.yml \
  --source-ref refs/heads/main \
  --source-digest "$(git rev-parse 'refs/tags/v<version>^{commit}')"
```

A check with `--repo` alone passes for any workflow and any ref of the repository. The release
journey makes the class-bound check for the prerelease and for every release it upgrades from.

A release pinned as `"github:HengYangDS/ethos" = "<version>"` gets the provenance
`github-attestations` in its Mise lock entry, which Mise records after it checks the archive at
lock time. Mise has no option that names the signer workflow or the source ref of a GitHub
attestation, so that record alone proves neither. Whether an install from the lock refuses bytes
that the lock does not bind is what the journey's two refusal cases establish for the Mise release
that CI binds; until both hold, an installation through the pin is described as checksum-verified.
The `http:` declaration that adopters pin today checks a checksum only.

## Storage And Currentness

Current readers select Attestations from `refs/ethos/attestations-set` and
validate the required predicate and exact bindings. Its internal
`evidence/attestations` paths belong to an independent Git object tree, not a
workspace directory. Neither a documentation path nor a profile directory
can select current proof.

Machine output under `build/ethos/` or `build/evidence/` is generated material.
A bounded Attestation records the verifier, subject, scope and exact result;
its required supporting objects must remain retrievable for its retention
lifecycle. A human explanation belongs with the semantic subject it explains,
not in a duplicate proof directory.

Committed historical Claims and Chronicles remain retrievable through Git;
see [History](../history/README.md). Their old state labels are dated
observations, not current readiness. Still-valid requirements belong to their
current specification, design or execution owner. Removing historical copies
from a checkout does not resolve an unfinished requirement or authorize
resource deletion.

## Optional Semantic Assurance

Digest-only propositions remain portable and require no provider, account,
daemon, credential, network, or dedicated local account. When semantic
assurance is required, one candidate-external Attestation binds the compiled
Commitment identity, evidence digest, semantic scope, exact HEAD, verifier,
validity interval, and non-authorizing verdict. Missing, malformed, stale,
repository-local, or mismatched assurance fails closed. This is a bounded
verifier statement, not cryptographic proof of independent semantic
correctness.

Status: see front matter.

Purpose: explain what a proof Attestation binds, how a release's files are attested and checked,
and how stored Attestations are read as current.

See also: [Documentation Root](../README.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
