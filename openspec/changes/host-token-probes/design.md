# Design

## Context

See the [proposal](proposal.md). The queue answers a token in `HostQueue.holds`: it splits the
token at its colon, requires a nonce of sixteen alphanumeric characters and a decimal process
number, and then asks whether a live ticket's name ends with `-<process number>-<nonce>`.

## Goals / Non-Goals

Goals:

- A test of the token that cannot fail for the nonce it happens to draw.
- Probes that reach the comparison, so the test binds "exactly one ticket's".

Non-Goals:

- Any change of `holds` or of the token's form.

## Decisions

1. **Every probe is derived from the token.**
   - **Rests on:** the token's form, `<nonce>:<process number>`, read in `Ticket.token`.
   - **Decision:** the well-formed probes are the nonce with the process number plus one, the
     process number with a nonce whose first character is replaced by another hexadecimal
     digit, and the nonce with the process number preceded by `1`. Each passes the shape check
     and differs from the token for every nonce.
   - **Why not keep the upper-case probe:** it differs from the token only when the nonce holds a
     letter.
2. **The malformed probes stay and gain two.** The patterns that a glob would have matched stay,
   and the empty token and a token without a nonce return.

## Risks / Trade-offs

- [The replaced first character could equal the original] -> The replacement is chosen as the
  digit that the original is not.

## Proof Strategy

The test passes on the lane's code. Two mutations of `holds` are run against it and each fails
it: a comparison of the nonce alone, and a comparison that ignores where the process number
begins.
