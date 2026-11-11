# Design

## Context

See the [proposal](proposal.md). `remote_parts` already parses URL and scp forms into host, port and
namespace path for fetch and push URLs.

## Goals / Non-Goals

Goals: every value that names a protected peer's location feeds its host, port and path.

Non-Goals: new forge keys, and declaring current values as `forgeFormer`.

## Decisions

1. `forgeRepository` values go through the same loop as `url` values; the separate path-only line
   is deleted, so one parse serves every location value.

## Risks / Trade-offs

A repository whose `forgeRepository` names another host than its fetch URL now protects that host
too, which the documentation already promised.
