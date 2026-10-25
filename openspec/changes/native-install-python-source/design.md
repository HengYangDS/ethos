# Design

## Context

The locked project environment may use Homebrew Framework Python. Runtime materialization already
resolves an installed, version/ABI/architecture-congruent copyable image through native uv discovery.
Package acceptance instead creates its console from the project interpreter before isolating PATH
and the data directory. The console then has neither a copyable base nor visible standalone supply.

## Goals / Non-Goals

**Goals:** use the existing image-source resolver before isolation; retain the project interpreter
for locked dependency supply; qualify the actual installed-console lifecycle.

**Non-Goals:** another resolver, a host-path exception, provisioning, environment migration,
weaker isolation, relaxed admission, or adopter activation.

## Decisions

Resolve the copyable interpreter at the existing acceptance entry boundary. Pass that exact
executable to native `uv venv`; continue preparing and installing locked dependencies with the
original project interpreter. The existing resolver owns congruence and source-layout validation.
Failure still stops before console creation. No host directory is hardcoded or added to the
isolated PATH, and no discovery answer survives the invocation.

## Risks / Trade-offs

The accepted image supply must already be installed. Missing supply remains an explicit failure,
not a download or fallback permission. Unit coverage distinguishes the two interpreter roles;
native package acceptance proves the isolated installed console can actually activate its runtime.

## Migration Plan

Reproduce the wrong interpreter binding, repair the existing caller, run focused delivery tests
and native quality checks, then qualify the packaged lifecycle and official archive projection.
Preserve failed full-proof evidence and existing release coordination holds.
