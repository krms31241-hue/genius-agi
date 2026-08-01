"""
Providers Configuration
Genius AGI

Manages:
- Multiple API keys
- Provider settings
- Key rotation state
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


CONFIG_PATH = Path(
    "data/providers_state.json"
)


@dataclass
class ProviderKeys:

    name: str

    keys: list[str] = field(
        default_factory=list
    )

    disabled: set[int] = field(
        default_factory=set
    )

    current: int = 0


    def available_keys(
        self,
    ) -> list[str]:

        return [
            key
            for index, key in enumerate(self.keys)
            if index not in self.disabled
        ]


    def next_key(
        self,
    ) -> str | None:

        if not self.keys:
            return None


        for _ in range(
            len(self.keys)
        ):

            index = self.current

            self.current = (
                self.current + 1
            ) % len(self.keys)


            if index not in self.disabled:

                return self.keys[index]


        return None




class ProvidersConfigManager:
    """
    Central provider configuration manager.
    """


    def __init__(
        self,
    ) -> None:

        load_dotenv()

        self.providers: dict[
            str,
            ProviderKeys
        ] = {}

        self._load_state()



    def register_provider(
        self,
        name: str,
        keys: list[str],
    ) -> None:
        """
        Register provider keys.
        """

        self.providers[name] = ProviderKeys(
            name=name,
            keys=keys,
        )



    def load_from_env(
        self,
    ) -> None:
        """
        Load provider keys from environment.

        Format:

        OPENAI_KEYS=key1,key2
        ANTHROPIC_KEYS=key1,key2
        """

        mapping = {

            "openai": "OPENAI_KEYS",

            "anthropic": "ANTHROPIC_KEYS",

            "gemini": "GEMINI_KEYS",

            "openrouter": "OPENROUTER_KEYS",

        }


        for provider, env_name in mapping.items():

            value = os.getenv(
                env_name,
                "",
            )


            if value:

                self.register_provider(
                    provider,
                    [
                        item.strip()
                        for item in value.split(",")
                        if item.strip()
                    ],
                )



    def get_key(
        self,
        provider: str,
    ) -> str | None:
        """
        Get next available key.
        """

        item = self.providers.get(
            provider
        )


        if not item:

            return None


        return item.next_key()



    def disable_key(
        self,
        provider: str,
        index: int,
    ) -> None:
        """
        Disable failed key.
        """

        item = self.providers.get(
            provider
        )


        if item:

            item.disabled.add(
                index
            )




    def _load_state(
        self,
    ) -> None:
        """
        Load saved rotation state.
        """

        if not CONFIG_PATH.exists():

            return


        try:

            data = json.loads(
                CONFIG_PATH.read_text()
            )


            for name, item in data.items():

                self.providers[name] = ProviderKeys(
                    name=name,
                    keys=item.get(
                        "keys",
                        [],
                    ),
                    disabled=set(
                        item.get(
                            "disabled",
                            [],
                        )
                    ),
                    current=item.get(
                        "current",
                        0,
                    ),
                )


        except Exception:

            logger.exception(
                "Failed loading provider state"
            )



    def save_state(
        self,
    ) -> None:
        """
        Save rotation state.
        """

        CONFIG_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )


        data = {}


        for name, item in self.providers.items():

            data[name] = {

                "keys": item.keys,

                "disabled": list(
                    item.disabled
                ),

                "current": item.current,
            }


        CONFIG_PATH.write_text(
            json.dumps(
                data,
                indent=2,
            )
        )



    def provider_config(
        self,
        name: str,
    ) -> dict[str, Any]:
        """
        Return provider configuration.
        """

        item = self.providers.get(
            name
        )


        if not item:

            return {}


        return {

            "api_keys": item.keys,

            "disabled_keys": list(
                item.disabled
            ),

        }



__all__ = [
    "ProviderKeys",
    "ProvidersConfigManager",
]

