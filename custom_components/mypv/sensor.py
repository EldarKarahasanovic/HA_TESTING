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

from homeassistant.helpers.entity_registry import async_get

async def async_setup_entry(hass, entry, async_add_entities):
    """Add or update my-PV entry."""
    coordinator: MYPVDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    if CONF_MONITORED_CONDITIONS in entry.options:
        configured_sensors = entry.options[CONF_MONITORED_CONDITIONS]
    else:
        configured_sensors = entry.data[CONF_MONITORED_CONDITIONS]

    entity_registry = async_get(hass)
    current_entities = [entity for entity in entity_registry.entities.values() if entity.platform == DOMAIN and entity.config_entry_id == entry.entry_id]

    current_sensor_ids = [sensor.entity_id for sensor in current_entities if isinstance(sensor, MypvDevice)]
    new_sensor_ids = [f"{entry.entry_id}_{sensor}" for sensor in configured_sensors]

    # Remove entities that are no longer in configuration
    sensors_to_remove = [entity for entity in current_entities if isinstance(entity, MypvDevice) and f"{entry.entry_id}_{entity._sensor}" not in new_sensor_ids]
    for entity in sensors_to_remove:
        entity_registry.async_remove(entity.entity_id)

    # Add new entities
    entities_to_add = [MypvDevice(coordinator, sensor, entry.title) for sensor in configured_sensors if f"{entry.entry_id}_{sensor}" not in current_sensor_ids]
    async_add_entities(entities_to_add)




class MypvDevice(CoordinatorEntity):
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
                if relOut is not None and loadNom is not None:
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
