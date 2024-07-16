"""The MYPV integration."""

import logging
from homeassistant.const import CONF_MONITORED_CONDITIONS
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import slugify
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.const import (
    ELECTRIC_CURRENT_AMPERE,
    FREQUENCY_HERTZ,
    TEMP_CELSIUS,
)

from .const import SENSOR_TYPES, DOMAIN, DATA_COORDINATOR, MYPV_DEVICES
from .coordinator import MYPVDataUpdateCoordinator
from .trans import my_pv_trans

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Add an MYPV entry."""
    coordinator: MYPVDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    if (
        "polling_interval" in entry.options
        and entry.options["polling_interval"] != coordinator.update_interval
    ):
        coordinator.set_interval(entry.options["polling_interval"])

    entities = []

    if "use_all_sensors" in entry.options and entry.options["use_all_sensors"]:
        for sensor in SENSOR_TYPES:
            entities.append(MypvDevice(coordinator, sensor, entry.title))
    elif CONF_MONITORED_CONDITIONS in entry.options:
        for sensor in entry.options[CONF_MONITORED_CONDITIONS]:
            entities.append(MypvDevice(coordinator, sensor, entry.title))
    else:
        for sensor in entry.data[CONF_MONITORED_CONDITIONS]:
            entities.append(MypvDevice(coordinator, sensor, entry.title))
    async_add_entities(entities)


class MypvDevice(CoordinatorEntity, SensorEntity):
    """Representation of a MYPV device."""

    def __init__(self, coordinator, sensor_type, name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        if sensor_type not in SENSOR_TYPES:
            raise KeyError
        self.coordinator = coordinator
        self._sensor = SENSOR_TYPES[sensor_type].name_long
        self._name = name
        self.type = sensor_type
        self._data_source = SENSOR_TYPES[sensor_type].source
        self._last_value = None
        self._unit_of_measurement = SENSOR_TYPES[self.type].unit
        self._icon = SENSOR_TYPES[self.type].icon

        self.serial_number = self.coordinator.data["info"]["sn"]
        self.fwversion = self.coordinator.data["info"]["fwversion"]
        self.model = self.coordinator.data["info"]["device"]
        _LOGGER.debug(self.coordinator)

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._sensor}"

    @property
    def unique_id(self):
        """Return unique id based on device serial and value key."""
        return "mypv {} {}".format(self.serial_number, self.type)

    # @property
    # def entity_id(self):
    #    """entity id"""
    #    if not self.entity_id:
    #        return "sensor." + slugify(self.unique_id)
    #    return None

    @property
    def state(self):
        """Return the state of the device."""
        try:
            state = self.coordinator.data[self._data_source][self.type]
            if self.type == "power_act":
                rel_out = int(self.coordinator.data[self._data_source]["rel1_out"])
                load_nom = int(self.coordinator.data[self._data_source]["load_nom"])
                state = (rel_out * load_nom) + int(state)
            self._last_value = state
        except Exception as ex:
            _LOGGER.error(ex)
            state = self._last_value
        if state is None:
            return state
        if self._unit_of_measurement == FREQUENCY_HERTZ:
            return state / 1000
        if self._unit_of_measurement == TEMP_CELSIUS and self.type != "tempchip":
            return state / 10
        if self._unit_of_measurement == ELECTRIC_CURRENT_AMPERE:
            return state / 10
        trans_key = f"info_{self.type}_{str(state)}"
        if "status" == self.type:
            trans_key = f"info_state_{MYPV_DEVICES[self.model]}_{str(state)}"
        elif self.type in ["m1devstate", "m2devstate", "m3devstate", "m4devstate"]:
            if state & 1:
                trans_key = "info_measure_devstate_err1"
            elif state & 2:
                trans_key = "info_measure_devstate_err2"
            elif state & 4:
                trans_key = "info_measure_devstate_err3"
            elif state & 8:
                trans_key = "info_measure_devstate_err4"
            else:
                return state
        if trans_key in my_pv_trans:
            return str(state) + my_pv_trans[trans_key][0]  # 0 = deutsch
        return state

    @property
    def state_class(self):
        """state class"""
        if self.type == "power":
            return SensorStateClass.MEASUREMENT
        return None

    @property
    def device_class(self):
        """state class"""
        if self.type == "power":
            return SensorDeviceClass.POWER
        return None

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return icon."""
        return self._icon

    @property
    def device_info(self):
        """Return information about the device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.serial_number)},
            manufacturer="MYPV",
            model=self.model,
            name=self._name,
            sw_version=self.fwversion,
            hw_version=None,
        )
