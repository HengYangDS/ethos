## MODIFIED Requirements

### Requirement: Hosted provider observations remain evidence-class scoped

ETHOS SHALL capture hosted provider observation envelopes without treating local
tool discovery or provider CLI output as repository proof. Each supported
provider SHALL name a runtime repository-target variable in tracked
configuration, and execute mode SHALL invoke the provider CLI only with the
resolved explicit repository target. The envelope SHALL derive bounded provider
observation state and gap codes without adding those gaps to repository proof
requirements.

#### Scenario: Provider observation envelope is captured

- **WHEN** hosted provider observation runs in dry-run or execute mode
- **THEN** the evidence SHALL name GitHub and GitLab provider observation state
- **AND** it SHALL include the Git head, remote URL, command, tool availability,
  target variable, resolved target, target configuration state, and execution
  state
- **AND** execute mode with a configured target SHALL add the provider-native
  --repo selector to the GitHub or GitLab command
- **AND** execute mode SHALL normalize provider facts such as latest observed
  head, status, conclusion, ref, and URL when the provider CLI returns them
- **AND** the envelope SHALL summarize provider states and stable observation
  gap codes as observed, partial, not_configured, or observation_failed
- **AND** it SHALL explicitly set hosted GitHub status claimed, hosted GitLab
  status claimed, and remote publication claimed to false unless separate
  hosted facts are promoted through the publication evidence class

#### Scenario: Unconfigured provider remains a bounded observation

- **WHEN** execute mode has no value for a provider repository-target variable
- **THEN** that provider SHALL report observation_state=not_configured
- **AND** the provider command SHALL NOT execute
- **AND** executed SHALL remain false and provider facts SHALL remain empty
- **AND** the envelope SHALL report a provider_not_configured observation gap
- **AND** the absent provider configuration SHALL NOT become a repository proof
  failure or a hosted success claim
