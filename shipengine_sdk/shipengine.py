"""The entrypoint to the ShipEngine API SDK."""
from typing import Dict
from typing import Union

from .shipengine_config import ShipEngineConfig


class ShipEngine:
    config: ShipEngineConfig
    """
    Global configuration for the ShipEngine API client, such as timeouts,
    retries, page size, etc. This configuration applies to all method calls,
    unless specifically overridden when calling a method.
    """

    def __init__(self, config: Union[str, Dict[str, any]]) -> None:
        """
        Exposes the functionality of the ShipEngine API.

        The `api_key` you pass in can be either a ShipEngine sandbox
        or production API Key. (sandbox keys start with "TEST_")
        """

        if type(config) is str:
            self.config = ShipEngineConfig({"api_key": config})
        elif type(config) is dict:
            self.config = ShipEngineConfig(config)
