## ADDED Requirements

### Requirement: Gap codes are a registered vocabulary

Every gap code that the product raises SHALL be registered in one packaged table, by a row or as
a member of a declared family prefix. A row SHALL state the code's owning package and MAY state a
one-line meaning, the detail that follows the code's colon, and a fixed repair. A test SHALL
refuse a code raised in the sources and unregistered, and a row that occurs in no source and is
not declared reserved. An unregistered code at run time SHALL be reportable and SHALL NOT raise.

#### Scenario: A new gap code without its row is refused

- **WHEN** a source module raises a code that the registry does not carry
- **THEN** the static registry test fails and names the code and its site

#### Scenario: An unregistered code stays reportable

- **WHEN** a result carries a gap whose code the registry does not carry
- **THEN** the loader reports it as unregistered, and no reader raises for it
