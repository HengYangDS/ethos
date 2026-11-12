# Design

Five reviewers (agent experience, product and community, security and evidence, contract and
architecture, adopters and fleet) converged on this design over three rounds on 2026-11-12, with no
rejection and no remaining blocking objection; the owner then decided D1 to D7 (decision 12). Line
references are to `d72001921`, the base the reviewers checked. "rc" is the archived `rc-plan`
design, "res" the 2026-11-07 committee's resolution, "TP" the terminal plan.

## Context

- **The first run** (a newcomer agent, 2026-11-12, an editable console in a lane): no install step
  in any entry document; a passing proof after 24.6 minutes and 50 steps, 40 of them `ethos` calls
  and 14 blocked or failed; accepted `dev` after 27.8 minutes; three blockers cleared only from
  source. The `foundation` starter that `adopt --create` writes fails `prove` with 8 paradigm gaps
  while `status` says `ready`.
- **The hidden normal path:** root help lists six commands and the `attestation` and `host` groups;
  `lane` (12 direct commands and 14 more in four nested groups) and `hook` are hidden, as
  `catalog-groups` chose, although R1 made lane operations public (res:61-65). 9 of 18 command
  continuations lacked `--root`, and one result carried six next-step fields that disagreed.
- **Evidence:** hosted CI runs on pushes and pull requests and release assets carry Sigstore build
  provenance; the proof Attestations stay in `refs/ethos/attestations-set`, and publication admits
  only branch and tag targets (`repository/release/publication.py:52-68`).
- **Adopters:** 39 `rebind-ethos-*` Changes in eight repositories between 10-25 and 11-12; the pins
  that exist are hand-pasted `http:ethos` tables or a CI source commit, five repositories have none,
  and `adopt` writes none (C3 adds the writer, rc:598-600).
- **The market** (41 products studied): spec-driven tools are free and large; distribution runs
  through agent directories; agent clients ship hooks that fail open by default and their own
  worktrees; forges ship agent governance on one forge each; merge queues land only tested trees;
  gittuf keeps ref policy off the forge; receipt products are commercial or early. No open product
  binds accepted intent, the exact landed tree, its gate results and a compare-and-swap landing
  across forges.

## Goals / Non-Goals

Goals:

- One stated position, with its limits, that the kernel already supports.
- A public normal path from adoption to retirement that an agent completes from `next` alone, with
  decidable budgets for what an agent pays.
- A first hour that reaches read-only value in minutes and a landed change without reading source.
- Adopters upgrade by one reviewed pin change.

Non-Goals:

- No hosted service, account or dashboard; no claim to replace code review.
- No intent authoring of ETHOS's own; OpenSpec stays the sole Change carrier (PDC:119-126).
- No command aliases; no second Skill owner for a repository; no store shared between user accounts.
- ETHOS owns neither adopters' toolchains nor the lifecycle of worktrees that agent clients create;
  client worktree adapters are withdrawn until a named outside user asks.
- No SLSA level claimed without an assessment; no export store, and a published export is durable.

## Decisions

1. **Position.** ETHOS is the local-first landing gate for changes that agents write, owned by the
   repository: a change lands on the accepted branch only when it matches an accepted OpenSpec
   Change and passes the repository's own gates on the exact tree, whichever agent wrote it, and
   each landing is signed and attested on the local plane. Short form: "nothing lands that your
   repository has not checked". Three limits go wherever the position appears: the record is local
   and self-attested today; until an independent approver exists the caller authorizes its own
   landing; ETHOS decides only as the sole writer of the accepted branch, so the forge reserves it
   for the identity that runs `ethos publish`. What is distinctive is the combination, not any one
   part; ETHOS complements OpenSpec, integrates with agent clients' hooks and forges as proof
   planes, and competes with receipt products on binding, not on openness.
2. **Users.** The entry user for the next 12 months: solo maintainers and small teams who plan in
   OpenSpec, run agent sessions in parallel and let ETHOS own the accepted branch, on macOS or
   Linux; many repositories is the expansion. The agent is the first user of every surface. Teams
   that require pull requests get the flow PDC:261-271 defines, designed but not yet tested end to
   end: the `proposal/*` ref is reviewed on the forge, the maintainer lands the exact reviewed
   object by CAS, and the required check is the CI carrier's check run from a pinned source.
3. **The shape stays** (res §6 B): one application package and catalog, projected to CLI, Git hooks,
   CI carriers, a version-matched Skill, stateless MCP and later an SDK.
4. **The public normal path.** Every operation from adoption to retirement is shown in help and
   reachable through `next`; protocol entry points (`hook admit`, `commit-range`, `ref-update`,
   `ref-transaction`) stay namespaced and are marked; no aliases. N4 MODIFIES `Public Command Plane`
   and PDC:366, restoring R1's amendment, and `Group commands are catalog operations`, so root and
   group help list names and summaries with full schemas only at the leaf; the Change that measures
   it lowers the 48 KiB help ceiling.
5. **Agent budgets,** each a declared ceiling in its owner, lowered by the Change that measures it,
   with timing reported and never gating:
   - gating in A17's RC acceptance (owner decision D2): calls from the install line to the `adopt`
     preview on published bytes (B1); calls for one Change from an unadopted repository to a retired
     lane (B2); zero self-loops and blocked steps (B3); every `next.argv` runs verbatim from a fresh
     shell (B4); every fixture exits by its declared exit kind (B5); results within the declared
     payload budgets with no gap dropped (B6); no operator script on the golden path (B8); one
     authoritative `next` per result (B11); and, once A10 implements it, one safe next step after a
     kill at each effectful step with nothing applied twice (B10);
   - reported: cold start (B7), bytes per repository and host (B9), bytes and seconds per journey
     (B12), the bump's cost (B13, gating in 0.3.0) and adopter lag (B14, with B3).
6. **The first hour.** A7 ships the `inputs` reader in beta.10, and A7 and N1 emit `inputs` from the
   next release (rc:362-363). N1, after A7 and on its typed steps: `status` names the way in outside
   a repository without offering `git init`, routes a plain repository to the `adopt` preview and a
   fresh formation to today's `lane start`, and owns `plan --changed` after a commit. N2: every
   starter passes its own proof after formation, the preview reports bytes, `prove` points to
   `repair-paradigm`, and commit identity is checked first. N3: the formation digest is stable
   across symlinked paths. N5: install, `status`, `adopt`, `adopt --exit` and "follow `next`", from
   a fixture the journey runs. N6: the four maintainer Skills are marked internal. The first change
   without source waits for A9.
7. **Evidence others can see,** a 0.3.0 direction, each step its own Change after C1 and DR-0022's
   build identity: first a PDC obligation, plane and retention for evidence a release's consumer can
   check; then a landing-attestation export, a signed, self-attested projection from the local plane
   that never authorizes an effect, binding the source Attestations, scope, plane, the CAS effect,
   `gitCommit` and `gitTree` subjects, the release by tag name and commit, absence reasons and the
   previous export's hash, from the permanent landing-effect records; an in-toto Statement in SLSA
   v1.2's Verification Summary form with no Source Track claim; one signature format proved on macOS
   and Linux; one export per build as a release asset with its hash in the signed tag; a dedicated
   key; a closed field allowlist; and `ethos attestation verify`.
8. **Channels.** Runtime channels stay as res §6 A decided. `skill install` (A15) links each
   repository's own untracked project skill directory from that repository's `CURRENT`, with an
   ignore rule that A15 owns, so no host link fixes one version across repositories. A plugin waits
   for a named consumer and for C1's attested claim; it is a pointer that owns no guidance, built
   from the release tag, with no hooks, no MCP server and no install step, deferring to a
   repository's pin; directories come only at G2 with a design that meets their policies.
9. **Footprint.** The per-user host store already holds released runtimes by digest; the 680 MB came
   from an editable console. Measure B9 on a released install, route per-repository copies to the
   runtime owner and tool copies to Mise and uv, keep R7(c)'s budgets as RC items, and finish
   R7(a)'s previewed release of consumers whose repository has disappeared (D.5); a returning
   consumer refuses with one re-pin step.
10. **The fleet.** The adopter bump is its own RC Change after C3 (owner decision D7): one preview
    and apply in a lane that changes the one pin line, relocks, previews `repair-paradigm` and
    `lane project --check`, adds the changelog line, and moves the CI Mise bootstrap with the pin.
    R9's fleet migration gives the unpinned repositories their one pin line; B3 renders the adopter
    impact into the release notes and reports lag; after B3, a release with no adopter impact may be
    skipped (D5).
11. **Order.** The RC order stands (rc Decision 2): disjoint owners in parallel, A17 after B6, and
    `release-provenance` then C1, then C2 and C3, on the golden path's critical path. The first-hour
    Changes need only what is on `dev`, with A7 before N1. Family 3 (D.5, E and
    `proof-output-scratch`), then A9 with its own model-free local journey test that does not stand
    for R1's hosted acceptance, come next.
12. **Owner decisions of 2026-11-12:**
    - D1: document the install now, claiming checksum verification only where a pin table or lock
      exists and TLS only elsewhere, amending R10 and rc Decision 5(6) until C1 and C3 replace it
      with one attested line, with C5 as the exit of the documented `http:ethos` table.
    - D2: the gating budgets join A17's RC acceptance.
    - D3: done on GitHub the same day: private vulnerability reporting enabled, topics and
      description set, Discussions closed until G1; `SECURITY.md` follows as a Change; design
      partners are not contacted until the owner approves each contact.
    - D4: the pointer plugin as decision 8 states.
    - D5: as decision 10 states.
    - D6: the GitHub account in install lines and manifests is a distribution identity, not a peer;
      no per-peer Source VSA.
    - D7: the adopter bump is an RC item.

## Risks / Trade-offs

- A forge ships open agent receipts; agent clients absorb lanes; OpenSpec moves fast (2.0 needed a
  skill-ownership rule the day it arrived).
- Docs that teach command forms A9 retires; N5 says "follow `next`" for the first change.
- One maintainer after G1; self-authorized landing until an independent approver; per-release
  adopter cost until C3 and B3.
- Publishing an export cannot be undone; signer compromise or conflicting exports.
- Unknowns: outside demand; the export's redaction cost; a Python console's cold-start floor.

## Open Questions

- A domain the product owns, for the export's predicate type, a DNS-verified MCP namespace and
  peer-neutral docs, before decision 7 and the MCP Registry.
