import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import async_add_entities

from .const import DOMAIN, DATA_COORDINATOR, CONF_HOST, PLATFORMS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the boost button."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    host = entry.data[CONF_HOST]
    
    # Check if the entity is already set up
    existing_entities = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("entities", [])
    if any(entity.unique_id == f"{entry.entry_id}_boost_button" for entity in existing_entities):
        _LOGGER.debug("Boost button already exists")
        return True

    # Add new boost button
    _LOGGER.debug("Adding boost button")
    async_add_entities([BoostButton(coordinator, host, entry.title)], True)

    return True

class BoostButton(ButtonEntity):
    """Representation of a Boost Button."""

    def __init__(self, coordinator, host, title):
        """Initialize the button."""
        self.coordinator = coordinator
        self.host = host
        self._title = title
        self._unique_id = f"{self.host}_boost_button"
        self._name = f"{self._title} Boost Button"

    @property
    def unique_id(self):
        """Return the unique ID of the button."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the button."""
        return self._name

    async def async_press(self):
        """Handle the button press action."""
        # Implement the button press logic here
        pass
