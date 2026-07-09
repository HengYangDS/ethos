## MODIFIED Requirements
### Requirement: Product Boundary and Contributor Policy Gate
ETHOS SHALL keep active product surfaces, release metadata, and contributor
policy organization-native rather than person-native or adopter-private.

#### Scenario: Enterprise readiness aggregates closeout layers
- **WHEN** `ethos quality enterprise-readiness --json` runs
- **THEN** ETHOS reports every enterprise closeout planning layer from L0 through L8
- **AND** the report lifts required gaps from workspace status, report scorecard, product boundary, docs topology, contributor policy, governance context, generic parity, generated artifacts, release policy, and claim-carrier checks
- **AND** the report is clean only when every layer is clean
- **AND** the report states that remote publication, external adopter retirement, and foreign Work Lane cleanup are outside the local closeout claim unless separately authorized.
