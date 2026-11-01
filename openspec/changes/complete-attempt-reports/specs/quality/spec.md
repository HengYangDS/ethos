## ADDED Requirements

### Requirement: Report admission names cases as their producers do

Report admission SHALL match each Allure result to an executed case by the name allure-pytest gives
that case: the package and classes from allure-pytest's parser and the test from the case's original
function name. A refusal SHALL name the cases that differ.

#### Scenario: A parameter id contains the node separator

- **WHEN** a parametrized case's id contains `::`, such as `agent::thread:id`
- **THEN** its Allure result and its executed case carry the same name
- **AND** hosted verification admits the attempt's Allure results.

#### Scenario: An executed case has no result

- **WHEN** one executed case has no Allure result
- **THEN** admission refuses the results
- **AND** the refusal names that case.
