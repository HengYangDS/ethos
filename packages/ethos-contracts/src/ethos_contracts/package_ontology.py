from __future__ import annotations

TARGET_PACKAGES = (
    "ethos-core",
    "ethos-contracts",
    "ethos-repository",
    "ethos-assistants",
    "ethos-adapters",
    "ethos",
    "ethos-test",
)

MIGRATION_HOSTS = (
    "ethos-kernel",
    "ethos-governance",
    "ethos-workspace",
    "ethos-agent",
    "ethos-project",
)

TARGET_DISTRIBUTIONS = ("distributions/npm",)
MIGRATION_DISTRIBUTIONS = {
    "distributions/npm": {
        "state": "planned_not_migrated",
        "migration_host": "packages/ethos-node",
    },
}

MIGRATION_DISPOSITIONS = {
    "ethos-kernel": "migrate kernel algebra to ethos-core and contracts to ethos-contracts",
    "ethos-governance": "split contracts, repository semantics, and provider adapters",
    "ethos-workspace": "split lifecycle semantics from Git and SQLite providers",
    "ethos-agent": "move assistant semantics to ethos-assistants and protocols to adapters",
    "ethos-project": "move adoption semantics to repository and scaffold writers to adapters",
}
MIGRATION_HOST_LIFECYCLE = {
    package: "migration-host" for package in MIGRATION_HOSTS
}


def package_ontology_report() -> dict[str, object]:
    return {
        "target_packages": list(TARGET_PACKAGES),
        "migration_hosts": list(MIGRATION_HOSTS),
        "target_distributions": list(TARGET_DISTRIBUTIONS),
        "migration_distributions": dict(MIGRATION_DISTRIBUTIONS),
        "migration_dispositions": dict(MIGRATION_DISPOSITIONS),
        "migration_host_lifecycle": dict(MIGRATION_HOST_LIFECYCLE),
    }
