from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import CONF_HOST
import aiohttp
import logging

from .const import DOMAIN, DATA_COORDINATOR

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the toggle switch."""
    coordinator: MYPVDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    host = entry.data[CONF_HOST]

    # Ensure no duplicate entities are added
    existing_entities = hass.data[DOMAIN].get(entry.entry_id, {}).get("entities", [])
    if any(entity.unique_id == ToggleSwitch.get_unique_id(host) for entity in existing_entities):
        _LOGGER.warning("Toggle switch entity already exists")
        return

    _LOGGER.warning("Adding toggle switch")
    async_add_entities([ToggleSwitch(coordinator, host, entry.title)], True)
    
class ToggleSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, host, name):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._device_name = name
        self._name = "Device state"
        self._switch = "device_state"
        self._host = host
        self._icon = "mdi:power"
        self._is_on = self.coordinator.data.get("setup", {}).get("devmode", False)
        self._model = self.coordinator.data.get("info", {}).get("device", "Unknown")
        self.serial_number = self.coordinator.data.get("info", {}).get("sn", "Unknown")
    
    @property
    def is_on(self):
        if self.coordinator.data:
            self._is_on = self.coordinator.data.get("setup", {}).get("devmode", False)
        return self._is_on

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
        return ToggleSwitch.get_unique_id(self._host)

    @staticmethod
    def get_unique_id(host):
        """Generate unique ID for the switch entity."""
        return f"{DOMAIN}_{host}_device_state"

    async def async_turn_on(self):
        await self.async_toggle_switch(1)
        self._is_on = True
        await self.coordinator.async_refresh()
        self.async_write_ha_state()

    async def async_turn_off(self):
        await self.async_toggle_switch(0)
        self._is_on = False
        await self.coordinator.async_refresh()
        self.async_write_ha_state()
    
    async def async_toggle_switch(self, mode):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{self._host}/data.jsn?devmode={mode}") as response:
                if response.status != 200:
                    _LOGGER.error(f"Failed to turn on/off the device {self.unique_id}")
