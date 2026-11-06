## ADDED Requirements

### Requirement: A repository session obtains native tools through the repository's own mise

A repository session that materializes a locked native tool SHALL obtain it through the repository's
own digest-bound mise on every host, so that whether a host stages the tool or puts mise on PATH
cannot change the result. The staging command SHALL accept every tool that the native supply
registry declares.

#### Scenario: A hosted job did not stage the tool

- **WHEN** a hosted job that staged only Vale runs a session that needs Grype
- **THEN** the session materializes Grype through the repository's mise and runs

#### Scenario: A session materializes a tool another way

- **WHEN** a repository CI module materializes a native tool without the repository's mise
- **THEN** the architecture check fails and names the call

#### Scenario: A registered tool is staged

- **WHEN** a job stages a tool that the native supply registry declares
- **THEN** the staging command accepts it
