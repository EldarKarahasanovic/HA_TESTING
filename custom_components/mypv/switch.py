import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import async_add_entities

from .const import DOMAIN, DATA_COORDINATOR, CONF_HOST, PLATFORMS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the toggle switch."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    host = entry.data[CONF_HOST]
    
    # Check if the entity is already set up
    existing_entities = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("entities", [])
    if any(entity.unique_id == f"{entry.entry_id}_device_state" for entity in existing_entities):
        _LOGGER.debug("Toggle switch already exists")
        return True  

    # Add new toggle switch
    _LOGGER.debug("Adding toggle switch")
    async_add_entities([ToggleSwitch(coordinator, host, entry.title)], True)

    return True

class ToggleSwitch(SwitchEntity):
    """Representation of a Toggle Switch."""

    def __init__(self, coordinator, host, title):
        """Initialize the switch."""
        self.coordinator = coordinator
        self.host = host
        self._title = title
        self._unique_id = f"{self.host}_device_state"
        self._name = f"{self._title} Device State"
        self._is_on = False

    @property
    def unique_id(self):
        """Return the unique ID of the switch."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def is_on(self):
        """Return the current state of the switch."""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        # Implement the logic to turn the switch on
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        # Implement the logic to turn the switch off
        self._is_on = False
        self.async_write_ha_state()
