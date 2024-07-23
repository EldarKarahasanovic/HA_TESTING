from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import CONF_HOST
import aiohttp
import logging

from .const import DOMAIN, DATA_COORDINATOR

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the boost button."""
    coordinator: MYPVDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    host = entry.data[CONF_HOST]

    # Ensure no duplicate entities are added
    existing_entities = hass.data[DOMAIN].get(entry.entry_id, {}).get("entities", [])
    if any(entity.unique_id == BoostButton.get_unique_id(host) for entity in existing_entities):
        _LOGGER.debug("Boost button entity already exists")
        return

    _LOGGER.debug("Adding boost button")
    async_add_entities([BoostButton(coordinator, host, entry.title)], True)

class BoostButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, host, name) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._icon = "mdi:heat-wave"
        self._name = "Boost button"
        self._device_name = name
        self._host = host
        self._model = self.coordinator.data.get("info", {}).get("device", "Unknown")
        self.serial_number = self.coordinator.data.get("info", {}).get("sn", "Unknown")
        self._button = "boost_button"

    @property
    def name(self):
        return self._name
    
    @property 
    def icon(self):
        return self._icon
    
    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, self.serial_number)},
            "name": self._device_name,
            "manufacturer": "my-PV",
            "model": self._model,
        }
    
    @property
    def unique_id(self):
        """Return unique id based on device serial and variable."""
        return BoostButton.get_unique_id(self._host)

    @staticmethod
    def get_unique_id(host):
        """Generate unique ID for the button entity."""
        return f"{DOMAIN}_{host}_boost_button"

    async def async_press(self) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{self._host}/data.jsn") as response:
                if response.status == 200:
                    data = await response.json()
                    boost_active = data.get("boostactive", False)
                    new_boost = not boost_active
                    async with session.get(f"http://{self._host}/data.jsn?bststrt={int(new_boost)}") as response2:
                        if response2.status != 200:
                            _LOGGER.error("Failed to (de-)activate boost")
                else:
                    _LOGGER.error("Failed to get boost status")
