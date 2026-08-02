import asyncio
import logging
from executive.consent_service import ConsentService

from runtime.genius_runtime import GeniusRuntime


logging.basicConfig(
    level=logging.INFO
)



async def main():
    consent = ConsentService()

    if consent.needs_consent():
        print("\nGenius AGI requires permission to use system resources.")
        print("Available modes:")
        print("1 - Eco")
        print("2 - Balanced")
        print("3 - Performance")

        choice = input("Choose mode (1/2/3): ").strip()

        modes = {
            "1": "eco",
            "2": "balanced",
            "3": "performance",
        }

        mode = modes.get(choice, "balanced")
        consent.approve(mode)

        print(f"Resource mode set to: {mode}")

    runtime = GeniusRuntime()

    await runtime.initialize()


    while True:

        prompt = input(
            "\nGenius > "
        )

        if prompt.lower() in [
            "exit",
            "quit"
        ]:
            break


        result = await runtime.run(
            prompt
        )


        print(
            "\nAI:",
            result["response"]
        )


    await runtime.shutdown()



if __name__ == "__main__":

    asyncio.run(main())
