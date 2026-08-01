import pytest

from core.providers.provider_manager import ProviderManager


def test_provider_manager_exists():
    manager = ProviderManager()

    assert manager is not None
