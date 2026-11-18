# Design

## Context

A full proof runs its readiness gates without waiting, then takes its repository's slot and the
host's slot and waits for the load. The readiness gates of a small repository take tens of
seconds and those of ETHOS itself about three minutes; the sampling interval is fifteen seconds.

## Goals / Non-Goals

Goals:

- A proof on a quiet host with free slots starts its test gates when its readiness gates end.
- The guard stays: two samples within the limit, at least one interval apart, with no wait
  between them that the proof did not observe.

Non-Goals:

- The sampling interval, the limit, or how many samples admit.
- The proof's own load: a sample at admission that is above the limit, the proof's own
  readiness gates included, keeps the proof waiting as today.

## Decisions

1. **The first sample is taken before the readiness gates.**
   - **Rests on:** the readiness gates of every governed repository read so far run longer than
     one interval, so their own time is the interval that the rule asks for.
   - **Considered:** a shorter interval. It weakens the guard for every proof. And admitting on
     one sample when the 5-minute average is calm too: the rule of 2026-11-04 left that average
     because it lags a finished run by minutes.
   - **Chosen because:** the proof already spends the interval on work it must do.
   - **Applies to:** the proof operation, which reads the load, and the admission, which takes
     the sample.
2. **Any wait ends the run of calm samples.**
   - **Rests on:** the admission loop resets its count whenever it cannot sample, which is
     whenever it waits for a slot.
   - **Considered:** keeping the earlier sample across a wait for a slot. A proof that waited an
     hour behind another run would then be admitted on one fresh sample.
   - **Chosen because:** the earlier sample then counts only in the case the rule already
     trusts: nothing but the proof's own readiness gates lay between the two samples.
   - **Applies to:** the admission's first pass.

## Risks / Trade-offs

- A run of another session that starts and ends between the two samples is not seen as two
  busy samples; it was not seen by two samples fifteen seconds apart either, unless it fell
  into that window. The 1-minute average at admission still carries its last minute.
- The gain is fifteen seconds for each full proof on a declared host and nothing elsewhere.
