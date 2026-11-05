# Design

## Context

See [proposal.md](proposal.md). This is the first of two Changes that make publication peers
independent. It sets the address boundary: one structural rule that names address classes, applied
to tracked content, staged changes and new commit and tag messages. The second Change,
`peer-neutral-artifacts`, owns artifacts, evidence, `forge_repository` and the GitLab image source.

The directive from the ETHOS convergence session on 2026-11-05 asks for:

1. a Gitleaks rule in ETHOS's existing configuration that refuses RFC 1918 and RFC 4193 literals,
   loopback and link-local literals and hosts under `.local`, `.internal`, `.lan` and `.home.arpa`,
   allows RFC 5737, RFC 3849 and RFC 2606 forms, and names no address; red on a fixture with the
   LAN forge's address and port, green on one with `192.0.2.1` and `example.invalid`;
2. every private-class address in ETHOS's tracked content moved to a reserved form without changing
   what its test proves;
3. the same rule applied to whole commit messages and to tag messages at the existing owner,
   refusing a GitLab merge message whose project lives on a private host by structure, not by name;
4. one requirement, under 500 characters, with scenarios;
5. nothing that belongs to `peer-neutral-artifacts`.

The inputs that shape the decisions:

- The security review on 2026-11-05 found that addresses leak mainly through commit messages,
  Forge-stored release bodies and the evidence ETHOS writes, so a check of HEAD alone does not
  suffice. It proposed two layers: this structural rule, and a later push-time exact check.
- Adopter facts from DDWG and wib on 2026-11-05:
  1. wib's security gate and its hosted CI run Gitleaks in history mode with the default rules and
     no configuration. wib's history holds 3 private-class addresses, one of them in an ETHOS
     Attestation Set commit under `refs/ethos/`, and DDWG's holds about 12.
  2. wib's `evidence/` and DDWG's decision records DR-0001 and DR-0004 are immutable records, so
     rewriting a literal in them amends a record class that each repository never amends.
  3. Retiring `forge_repository` first requires `remote.<name>.forgeRepository` set locally
     wherever the remote is SSH.
- Owner decisions on 2026-11-05:
  1. One public distribution identity is allowed, the GitHub repository `HengYangDS/<repo>`. A
     private or LAN address may appear nowhere.
  2. History counts as disclosed. New leaks are blocked and current content is cleaned; history is
     purged only in the planned aigw and proxy rebuilds.
  3. DDWG's five public release bodies are edited, as Forge content outside this Change.
  4. The LAN GitLab registry stays off; GitLab CI keeps pulling the supply image from GHCR by
     digest, an accepted residual.

## Goals / Non-Goals

Goals:

- No private-class network address enters ETHOS's tracked content or a new commit or tag message
  of any governed repository, and the rule that refuses one names no address.

Non-goals:

- History, which counts as disclosed: no scan in this Change reads it.
- An exact check of named peer hosts and project paths, which needs each peer's identity.
- Adopters' content scans and records, Forge-stored release bodies, artifacts and evidence.

## Decisions

1. **One pattern, declared once.** The paradigm's `private_address` holds the pattern, and
   `RepositoryParadigm.names_private_address` applies it. ETHOS's Gitleaks rule
   `private-network-address` carries the identical string, and a test compares the two byte for
   byte. Gitleaks evaluates the pattern with RE2 and ETHOS with Python's `re`. The pattern uses
   only constructs that both engines read alike, and one corpus shows the same verdict in both.
2. **Classes, not addresses.** The pattern matches:
   - IPv4 literals in 10/8, 172.16/12, 192.168/16, 127/8 and 169.254/16;
   - IPv6 literals whose first group lies in fc00::/7 or fe80::/10, and the IPv6 loopback inside
     URL brackets or quotes;
   - names ending in `.local`, `.internal`, `.lan` or `.home.arpa` in host position: after `//` or
     `@`, or before `:<port>`.

   A bare suffix is not enough, because code and file names share it (`threading.local`,
   `version.local`, `settings.local.json`), and a bare `[::1]` is a Python slice. Token boundaries
   keep version strings and longer dotted numbers out, and a sentence-final period does not hide an
   address. Documentation ranges, reserved example names and the public identity
   (`github.com/HengYangDS/<repo>`, `ghcr.io/hengyangds/<image>`) pass by construction.

3. **Content and staged modes only.** ETHOS runs Gitleaks in two places: the pre-commit hook scans
   the staged change with `gitleaks git --staged`, and the `secrets` session scans a mirror of the
   tracked files with `gitleaks dir`. No ETHOS gate scans history. A test builds a repository whose
   history holds a private address and whose HEAD does not. Both consumers pass it, and a history
   scan of the same repository finds the address, so the pass is not vacuous.
4. **Adopters' content scans stay theirs.** The rule does not enter an adopter's Gitleaks
   configuration. wib scans history and DDWG's history holds old addresses, so the rule there would
   fail with no repair short of a history purge, which owner decision 2 rules out. An adopter that
   takes up the rule runs it in a content mode. The paradigm's message check does reach every
   governed repository, but only for new messages: in the `commit-msg` hook, in ETHOS's commit
   creation and in the commits that a publication introduces. A read-only scan of every ref and tag
   of 10 fleet repositories found no commit or tag message with a private-class address, so no
   existing range fails.
5. **Whole messages, quiet gaps.** Commit admission judges the subject with the commit grammar and
   the whole message with the pattern. The `commit-msg` hook reads the message above Git's scissors
   line, because `git commit --verbose` appends the staged diff below it, and a diff that removes an
   address must not block its own commit. Commit observation takes the message from the raw object
   that it already reads. The gap is `commit_message_private_address`, followed by the revision when
   there is one. It replaces the subject gap, which would repeat the subject, so no gap repeats the
   address.
6. **Tag messages at the tag owner.** `_immutable_tag_commit` admits every tag ref that ETHOS moves
   or publishes, so it judges the message beside the name and the signature and refuses with
   `release_tag_message_private_address`. ETHOS's own release tags carry the fixed message
   `Release <name>`.
7. **Merge messages by structure.** A GitLab default merge message ends with
   `See merge request <group>/<project>!<n>`, without the host. The pattern refuses the message when
   it names a private host, as a merge request URL does, and accepts the bare path. Whether a path
   belongs to a private peer is known only from the peer's identity, so that judgment belongs to
   the push-time exact check, not to a list of names in the paradigm.
8. **Redaction form for immutable records.** An immutable record may replace a private literal with
   `[redacted:private-network-address:hmac-sha256:<64 lowercase hex>]`. The digest is HMAC-SHA-256
   over the exact removed literal, keyed with a secret that the record's owner keeps in its
   credential store.
   - An unkeyed digest is refused. A private literal has little entropy: the 192.168/16 range with
     every port is 2^32 candidates, so anyone can enumerate an unkeyed digest back to the address.
   - The marker carries no address, so the rule accepts it, and a test shows that.
   - A record contract that admits redaction accepts a revision whose only differences replace
     pattern matches with markers. It can decide that from the diff, without the key. The owner
     verifies each marker with the key and the original literal.
   - Each adopter's record contract decides whether it admits redaction: wib's `evidence/`, DDWG's
     DR-0001 and DR-0004. This Change edits no adopter file.
   - ETHOS's own immutable root, `openspec/changes/archive/`, holds no private address, so ETHOS has
     no record to redact. The verifier lands with its first consumer.
9. **Current content.** At the base `be573e25b`, the pattern finds 29 lines in tracked content, and
   Python and Gitleaks find the same lines. Each moves to a reserved form, and each test proves what
   it proved before:
   - The kernel schema identifiers under the `ethos.local` host move to
     `https://ethos.invalid/schemas/<name>`: 4 generated by `terminal_schema_documents`, 15
     authored, and one test. RFC 2606 reserves `.invalid` for names that never resolve, which suits
     an identifier. No adopter or attestation reads the old identifiers.
   - 4 test sockets bind the name `localhost` instead of the IPv4 loopback literal. The bind and the
     tier guard's loopback reading do not change.
   - The retirement review fixture's self-hosted GitLab URL moves to `forge.test` and keeps its
     scheme and a non-default port. The module layout fixture's address value moves to RFC 5737.
10. **Neutral fixtures.** The tests join each private fixture when they use it, so tracked text
    names no private literal, and each one is a neutral example of its class. None is a real
    peer's address: a tracked test that joined the LAN forge's address would disclose it again in
    current content. The rule was shown red on the LAN forge's own address in a local run whose
    input stays outside the repository.
11. **The product boundary reads the same pattern.** ETHOS's product boundary gate already refused
    RFC 1918 and loopback hosts in URLs on ETHOS's product surfaces, with patterns of its own. It
    now takes the address classes from the paradigm's pattern and keeps only its own refusal of
    `localhost` endpoints, which a product surface must not fix but a message may name. The gate
    is ETHOS's own; a read-only search of the governed repositories found none that runs it, and
    ETHOS's product surfaces hold no match.

## Risks / Trade-offs

- A private name without host context, such as a bare host name in prose, passes. Literals are
  refused anywhere.
- A commit message that writes the IPv4 loopback literal is refused; the name `localhost` passes.
- RE2 and Python could diverge after a later edit of the pattern. The identity test and the shared
  corpus run with every change.
- Under decision 4, an adopter may keep a private address in content that its own scan does not
  read.

## Dependencies for `peer-neutral-artifacts`

- Retiring `forge_repository` first requires `remote.<name>.forgeRepository` set locally wherever
  the remote is SSH, as wib's GitLab remote is; otherwise the proposal review lookup fails.
- ETHOS writes peer URLs into evidence, including the Attestation Set commits under `refs/ethos/`
  that hold one of wib's historical addresses. Those write points belong to that Change.
- The push-time exact check of named peer hosts and project paths needs the peers' identities and
  follows both Changes.
