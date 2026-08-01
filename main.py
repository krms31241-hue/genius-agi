import asyncio
import logging

from runtime.genius_runtime import GeniusRuntime


logging.basicConfig(
    level=logging.INFO
)


async def main():

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
