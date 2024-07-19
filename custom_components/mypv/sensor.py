"""The my-PV integration."""

import logging
from homeassistant.const import CONF_MONITORED_CONDITIONS
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfFrequency,
    UnitOfTemperature,
)

from .const import SENSOR_TYPES, DOMAIN, DATA_COORDINATOR
from .coordinator import MYPVDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

async def async_setup_entry(hass, entry, async_add_entities):
    """Add a my-PV entry."""
    coordinator: MYPVDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    if CONF_MONITORED_CONDITIONS in entry.options:
        monitored_conditions = entry.options[CONF_MONITORED_CONDITIONS]
    else:
        monitored_conditions = entry.data[CONF_MONITORED_CONDITIONS]

    # Create a list to store the new entities
    new_entities = []

    for sensor in monitored_conditions:
        new_entities.append(MypvDevice(coordinator, sensor, entry.title))

    # Get the entity registry
    entity_registry = async_get_entity_registry(hass)

    # Get the current entities for the integration
    current_entities = hass.data[DOMAIN].get(entry.entry_id, {}).get('entities', [])

    # Find entities to remove
    entities_to_remove = [entity for entity in current_entities if entity.type not in monitored_conditions]

    # Remove entities that are no longer part of the monitored conditions
    for entity in entities_to_remove:
        entity_registry.async_remove(entity.entity_id)

    # Add new entities
    hass.data[DOMAIN].setdefault(entry.entry_id, {})['entities'] = new_entities
    async_add_entities(new_entities)



 
from homeassistant.helpers.entity import Entity

class MypvDevice(CoordinatorEntity, Entity):
    """Representation of a my-PV device."""

    def __init__(self, coordinator, sensor_type, name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor = SENSOR_TYPES[sensor_type][0]
        self._name = name
        self.type = sensor_type
        self._data_source = SENSOR_TYPES[sensor_type][3]
        self.coordinator = coordinator
        self._last_value = None
        self._unit_of_measurement = SENSOR_TYPES[self.type][1]
        self._icon = SENSOR_TYPES[self.type][2]
        self.serial_number = self.coordinator.data["info"]["sn"]
        self.model = self.coordinator.data["info"]["device"]
        _LOGGER.debug(self.coordinator)

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} {self._sensor}"

    @property
    def state(self):
        """Return the state of the device."""
        try:
            state = self.coordinator.data[self._data_source][self.type]
            if self.type == "power_act":
                relOut = int(self.coordinator.data[self._data_source]["rel1_out"])
                loadNom = int(self.coordinator.data[self._data_source]["load_nom"])
                state = (relOut * loadNom) + int(state)
            self._last_value = state
        except Exception as ex:
            _LOGGER.error(ex)
            state = self._last_value
        if state is None:
            return state
        if self._unit_of_measurement == UnitOfFrequency.HERTZ:
            return state / 1000
        if self._unit_of_measurement == UnitOfTemperature.CELSIUS:
            return state / 10
        if self._unit_of_measurement == UnitOfElectricCurrent.AMPERE:
            return state / 10
        return state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return icon."""
        return self._icon

    @property
    def unique_id(self):
        """Return unique id based on device serial and variable."""
        return "{} {}".format(self.serial_number, self._sensor)

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, self.serial_number)},
            "name": self._name,
            "manufacturer": "my-PV",
            "model": self.model,
        }

    async def async_remove(self):
        """Handle removal of entity."""
        await self.async_remove()
