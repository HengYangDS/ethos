# Proposal

## Why

The owner asked on 2026-11-14, as relayed, how the toolchain extends to further languages and
to a repository of mixed languages. Read on that day's `dev`: the paradigm knows 14 language
identities and no C or C++; three module rows, for Python, Node and Go; one locked toolchain owner
with three verbs. Two governed repositories use a second toolchain owner with a second Python lock
while being pure Python.

The release lead's ruling: one toolchain owner; several module rows in a repository, each
language with its own resolver and lock; a further language enters as a module row with the
resolver that its first real consumer uses; the native binary environment is a fourth
responsibility, admitted only with a named consumer and then under one lock for the native
environment and one owner of the Python lock.

## What Changes

- The paradigm's module table gains a row when a governed repository first needs it, by this
  ruling.
- The paradigm states the native environment's place when its first consumer is named.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The paradigm declaration and its module rows. No row is added on speculation.

Owner: the release lead. Next action: none until a consumer is named. Read again: after 0.2.0.
