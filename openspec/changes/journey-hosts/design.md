# Design

## Context

See the [proposal](proposal.md) and the [distribution delta](specs/distribution/spec.md).

Read in this tree on 2026-11-15:

- `journeyLegs` in `.config/ci/pipeline.cue` filters the release legs by two host names, and the
  generated journey job has two legs, `linux-x64` and `macos-arm64` (the workflow, read with a
  YAML parser).
- The release legs declare `linux-arm64` on the forge's native arm64 runner, required and not
  emulated. The model refuses a journey leg whose platform the release may leave out
  (`journey-leg-required`), and a required platform that is emulated (`release-required-native`).
- The journey tool names its host from the platform it runs on (`mise_target` in
  `tools/ci/toolchain/native.py`). Its one platform name is the leg that locks every published
  platform once, `linux-x64`; every other leg locks its own platform. It holds no list of hosts.
- The journey job takes the supply steps that the release job takes on the same runner
  (`githubHostSupplyAt`), and then calls the forge's client.
- The distribution specification lists no host. The Change that recorded DR-0021 left the list
  to that record.
- The release entries of 0.2.0-beta.7 to 0.2.0-beta.10 each name the Linux arm64 journey among
  what the beta does not qualify, because no hosted job runs it (`CHANGELOG.md`).

Not run: the journey on Linux arm64. A hosted run is its only venue here.

## Goals / Non-Goals

Goals:

- A release run and a journey dispatch run the adopter journey on Linux arm64, from the
  published Linux arm64 archive.

Non-Goals:

- Any change to the journey's steps, its receipt or its tool.
- A Windows journey.

## Decisions

1. **The journey's hosts are one named list in the model.**
   - **Rests on:** DR-0021, which declares the three hosts; the two compiled checks read above.
   - **Considered:** a third host name in the filter's condition, which is one line shorter and
     leaves the declaration inside an expression; every required release leg, which is the same
     three hosts today and would tie two declarations that DR-0021 states apart, a platform that
     a release must publish and a host whose journey the target declares.
   - **Chosen because:** the list reads as the declaration it is, and the existing check keeps
     something to refuse: a listed host that the release may leave out, which is how the model
     holds DR-0021's decision on Windows.
   - **Applies to:** the journey job of the forge that publishes the release, for a release run
     and for a journey dispatch. The legs keep the order of the release legs.
2. **No tool changes, and no new unit test of the journey.**
   - **Rests on:** the reading of the journey tool above: no branch depends on the host's name
     except the one that selects the full lock.
   - **Considered:** a unit case that runs the journey's steps for `linux-arm64` over fakes. It
     would execute the lines that the `macos-arm64` cases already execute.
   - **Chosen because:** what is unproved is the hosted runner, its tools and the published
     archive, and only a hosted run shows them. The pin of the generated job is the local
     regression.
   - **Applies to:** this Change. A defect that the first hosted leg finds gets its own
     regression.
3. **The delta adds one requirement and puts the hosts in a scenario's condition.**
   - **Rests on:** the specification and the records Change read above; the requirement
     `A hosted journey qualifies each published prerelease`, whose words "on macOS and Linux"
     stay true with a second Linux leg, and which the hermetic journey of the same batch
     modifies.
   - **Considered:** naming the three hosts in a requirement's text, which gives the list a
     second owner beside DR-0021; naming them in the neighboring requirement, which two Changes
     of one batch would then each carry whole, so that the one archived second undoes the first.
   - **Chosen because:** the requirement binds the journey to the target's declaration, and the
     scenario shows it for 0.2.0. It merges with either order of the two Changes.
   - **Applies to:** the distribution specification. DR-0021 stays the owner of the list.

## Risks / Trade-offs

- The leg has never run. Its first run is a journey dispatch on the lane's ref or the next
  release run.
- A leg upgrades from each predecessor on its own platform, so every predecessor needs a
  published Linux arm64 archive. That the releases adopters still select have one is not checked
  here; a predecessor without it fails the leg before any install.
- The journey calls the forge's client. That the native arm64 runner provides it is not verified
  here; no other job that the model places on that runner calls it.
- A listed host that no release leg declares yields no leg and no refusal. The pin of the
  generated legs shows a missing leg for the three hosts it names.
- A release run ends failed when the Linux arm64 leg fails, after the release is published. That
  is what the declaration asks: a beta whose journey fails on a declared host is not qualified.
