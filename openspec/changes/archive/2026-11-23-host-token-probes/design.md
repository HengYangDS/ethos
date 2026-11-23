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
     digit, the nonce with the process number preceded by `1`, and the nonce with the process
     number less its first digit. Each differs from the token for every nonce.
   - **Why not keep the upper-case probe:** it differs from the token only when the nonce holds a
     letter.
2. **The malformed probes stay and gain two.** The patterns that a glob would have matched stay,
   and the empty token and a token without a nonce return.
3. **The shape check stays, and the test binds it.**
   - **Rests on:** a mutation that removes the check passed every probe of this test's first
     form, and a reading of the comparison that seemed to explain why: a ticket's name is twenty
     digits, a dash, the process number, a dash and the nonce, so only a ticket's own two parts
     match its tail. A review of the removal showed the reading's premise. The listing returns
     every held `*.lock` file of the directory and checks no name. With a held file named
     `x--.lock` the comparison alone answers that the values `:` and the empty one hold a ticket,
     and with `a-b-c-d.lock` that `d:b-c` does.
   - **Decision:** the check is as it was. The test holds those two files and asks with those
     values, so the mutation that removes the check now fails it.
   - **Why not enforce the name's form in the listing instead:** that changes which files count
     as tickets for every reader, also beside an older release, and belongs to a change of its
     own.

## Risks / Trade-offs

- [The replaced first character could equal the original] -> The replacement is chosen as the
  digit that the original is not.
- [A held lock file with a ticket's tail and another head, such as `x-1-<sixteen letters>.lock`]
  -> `holds` answers for that tail, as in every release: the comparison reads the end of a name
  and the listing checks no name. Placing such a file needs write access to the queue directory,
  whose mode is 0700, and that user can enter a real ticket. Not changed here; reading whole
  names is the listing's change.

## Proof Strategy

The test passes on the lane's code. Three mutations of `holds` are run against it and each
fails it: a comparison of the nonce alone, a comparison that ignores where the process number
begins, and the removal of the shape check.
