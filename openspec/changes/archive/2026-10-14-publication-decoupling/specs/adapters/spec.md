## REMOVED Requirements

### Requirement: Source-owned Architecture Publisher integration

**Reason**: Architecture publication has an independent editorial owner; this
integration imposes drawing-specific source and proof maintenance on ETHOS.

**Migration**: Preserve exact editorial data and artwork outside ETHOS and
remove the integration, dedicated tests, dependencies and package callers.
Existing source Git history and accepted deliveries remain available.
