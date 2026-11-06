## ADDED Requirements

### Requirement: ETHOS's product surfaces carry no loopback or link-local literal

The product-boundary gate SHALL refuse a loopback or link-local literal on ETHOS's declared product
surfaces, in every form the private-address class refused before it excluded them.

#### Scenario: A product surface names a loopback address

- **WHEN** an ETHOS product surface names a loopback or link-local literal, bare, quoted or in any
  URL authority
- **THEN** the product-boundary gate reports `private_infrastructure_literal`
