## ADDED Requirements

### Requirement: A load sample from before the readiness gates counts once

A full executing proof SHALL read the host's 1-minute load once before its readiness gates. That
sample SHALL count as the first of the two consecutive samples that admit the proof only when it
fell within the limit, is at least one sampling interval old, and the proof took both slots
without waiting. In every other case the proof SHALL wait for two consecutive samples taken at
its admission.

#### Scenario: A quiet host admits a proof after its readiness gates

- **GIVEN** a load sample within the limit that the proof took before its readiness gates, and
  readiness gates that ran for at least one sampling interval
- **WHEN** both slots are free and the sample at admission falls within the limit
- **THEN** the proof is admitted without a further wait.

#### Scenario: An earlier sample does not replace a second look

- **WHEN** the earlier sample was above the limit, could not be taken, or is younger than one
  sampling interval, or the proof waited for a slot, or the sample at admission is above the limit
- **THEN** the proof waits until two consecutive samples at admission fall within the limit.
