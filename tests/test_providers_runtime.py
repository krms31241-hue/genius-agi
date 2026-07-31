import asyncio

from core.bootstrap.providers_bootstrap import (
    ProvidersBootstrap,
)


async def main():

    bootstrap = ProvidersBootstrap()

    manager = await bootstrap.initialize()

    print(
        "Providers:",
        manager.list_providers(),
    )

    print(
        "Count:",
        manager.provider_count(),
    )


    health = await manager.health()

    print(
        "Health:",
        health,
    )


if __name__ == "__main__":
    asyncio.run(main())
