from datetime import timedelta
import logging
import requests
import json

from async_timeout import timeout
from homeassistant.util.dt import utcnow
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class MYPVDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching MYPV data."""

    def __init__(self, hass: HomeAssistant, *, config: dict, options: dict):
        """Initialize global MYPV data updater."""
        self._host = config[CONF_HOST]
        self.config = config
        self.options = options
        self._info = None
        self._setup = None
        self._next_update = 0
        update_interval = timedelta(seconds=10)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    def update_config(self, config: dict):
        """Update configuration."""
        self.config = config
        self._host = config[CONF_HOST]

    def update_options(self, options: dict):
        """Update options."""
        self.options = options

    async def _async_update_data(self) -> dict:
        """Fetch data from MYPV."""
        def _update_data() -> dict:
            """Fetch data from MYPV via sync functions."""
            data = self.data_update()
            if self._info is None:
                self._info = self.info_update()

            if self._setup is None or self._next_update < utcnow().timestamp():
                self._next_update = utcnow().timestamp() + 120  # 2 minutes
                self._setup = self.setup_update()

            return {
                "data": data,
                "info": self._info,
                "setup": self._setup,
            }

        try:
            async with timeout(4):
                return await self.hass.async_add_executor_job(_update_data)
        except Exception as error:
            raise UpdateFailed(f"Invalid response from API: {error}") from error

    def data_update(self):
        """Update inverter data."""
        try:
            response = requests.get(f"http://{self._host}/data.jsn")
            response.raise_for_status()
            data = response.json()
            _LOGGER.debug("Data update: %s", data)
            return data
        except requests.RequestException as error:
            _LOGGER.error("Error fetching data: %s", error)
            raise UpdateFailed(f"Error fetching data: {error}")

    def info_update(self):
        """Update inverter info."""
        try:
            response = requests.get(f"http://{self._host}/mypv_dev.jsn")
            response.raise_for_status()
            info = response.json()
            _LOGGER.debug("Info update: %s", info)
            return info
        except requests.RequestException as error:
            _LOGGER.error("Error fetching info: %s", error)
            raise UpdateFailed(f"Error fetching info: {error}")

    def setup_update(self):
        """Update inverter setup."""
        try:
            response = requests.get(f"http://{self._host}/setup.jsn")
            response.raise_for_status()
            setup = response.json()
            _LOGGER.debug("Setup update: %s", setup)
            return setup
        except requests.RequestException as error:
            _LOGGER.error("Error fetching setup: %s", error)
            raise UpdateFailed(f"Error fetching setup: {error}")
