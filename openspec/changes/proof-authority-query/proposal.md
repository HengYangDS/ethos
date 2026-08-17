# Change: Select proof by exact operation authority

Candidate acceptance currently asks the generic proof reader for every current
repository proof at one HEAD. A valid historical Work Lane proof can therefore
invalidate an applicable repository proof after that lane and Lease generation
have been retired. Bind candidate acceptance to one explicit proof query and
retain fail-closed conflict detection inside that query. Capability:
`repository-governance`.
