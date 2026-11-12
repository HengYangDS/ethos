# Design

## Context

See the [proposal](proposal.md). GitHub shows a repository's `SECURITY.md` as its security policy
and offers the private report form on the **Security** tab once private vulnerability reporting is
on. The `product-form-plan` design (decision 1) states three limits wherever the product's position
appears.

## Goals / Non-Goals

Goals:

- A reporter finds one private route, what counts as a vulnerability and what to expect.
- The policy promises only what one maintainer can keep.

Non-Goals:

- A response-time commitment, a bounty or a disclosure timeline.
- An email address or any second route: the private report form is the only one.
- A policy for adopters' repositories; each repository owns its own.

## Decisions

1. The examples follow the product's trust promise: a change that lands without passing its gates
   on the exact tree, an Attestation forged or altered without the signing key, and a hook or
   command that runs code the repository did not declare.
2. The three limits from `product-form-plan` decision 1 are listed as documented limits, so a
   report about them is answered by the policy itself.
3. Fixes ship only in a new release, and earlier releases, prereleases included, are not patched.
   The wording holds before and after 0.2.0.
4. The Unreleased section gains one Added line; the next release entry carries it.

## Risks / Trade-offs

- A reporter may expect a response time. The policy says plainly that there is none.
- The examples are not a complete list; the policy says that they are examples.
