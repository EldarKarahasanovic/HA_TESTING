import logging
import voluptuous as vol
import requests
import json
import ipaddress
from requests.exceptions import HTTPError, ConnectTimeout, RequestException
from scapy.all import ARP, Ether, srp

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

from homeassistant.const import (
    CONF_HOST,
    CONF_MONITORED_CONDITIONS,
)
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, SENSOR_TYPES  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

DEFAULT_MONITORED_CONDITIONS = [
    "power1_solar",
    "temp1"
]

@callback
def mypv_entries(hass: HomeAssistant):
    """Return the hosts for the domain."""
    return set(
        (entry.data[CONF_HOST]) for entry in hass.config_entries.async_entries(DOMAIN)
    )

class MypvConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Mypv config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._errors = {}
        self._info = {}
        self._host = None
        self._filtered_sensor_types = {}

    def _host_in_configuration_exists(self, host) -> bool:
        """Return True if host exists in configuration."""
        return host in mypv_entries(self.hass)

    def _check_host(self, host) -> bool:
        """Check if we can connect to the mypv."""
        try:
            response = requests.get(f"http://{host}/mypv_dev.jsn", timeout=10)
            response.raise_for_status()
            self._info = response.json()
        except (ConnectTimeout, HTTPError) as e:
            self._errors[CONF_HOST] = "could_not_connect"
            _LOGGER.error(f"Connection error: {e}")
            return False
        except RequestException as e:
            self._errors[CONF_HOST] = "unexpected_error"
            _LOGGER.error(f"Unexpected error: {e}")
            return False
        return True
    
    def _get_sensor(self, host):
        """Fetch sensor data and update _filtered_sensor_types."""
        try:
            response = requests.get(f"http://{host}/data.jsn", timeout=10)
            response.raise_for_status()
            data = response.json()
            json_keys = set(data.keys())
            self._filtered_sensor_types = {}

            for key, value in SENSOR_TYPES.items():
                if key in json_keys:
                    self._filtered_sensor_types[key] = value[0]

            if not self._filtered_sensor_types:
                _LOGGER.warning("No matching sensors found on the device.")
        except RequestException as e:
            _LOGGER.error(f"Error fetching sensor data: {e}")
            self._filtered_sensor_types = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            self._host = user_input[CONF_HOST]
            if self._host_in_configuration_exists(self._host):
                self._errors[CONF_HOST] = "host_exists"
            else:
                can_connect = await self.hass.async_add_executor_job(
                    self._check_host, self._host
                )
                if can_connect:
                    await self.hass.async_add_executor_job(self._get_sensor, self._host)
                    return await self.async_step_sensors()

        # Perform ARP scan to find available hosts in the network
        available_hosts = await self.hass.async_add_executor_job(self._arp_scan)

        if not available_hosts:
            _LOGGER.warning("No hosts found on the network.")
        else:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_HOST): vol.In(available_hosts)
                }),
                errors=self._errors
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str
            }),
            errors=self._errors
        )

    def _arp_scan(self):
        """Perform ARP scan to find all hosts in the current network."""
        network = ipaddress.ip_interface(self.hass.config.api.base_url).network
        arp = ARP(pdst=str(network))
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether/arp
        result = srp(packet, timeout=3, verbose=False)[0]

        available_hosts = []
        for sent, received in result:
            available_hosts.append(received.psrc)

        return available_hosts

    async def async_step_sensors(self, user_input=None):
        """Handle the sensor selection step."""
        if user_input is not None:
            return self.async_create_entry(
                title=f"{self._info['device']} - {self._info['number']}",
                data={
                    CONF_HOST: self._host,
                    CONF_MONITORED_CONDITIONS: user_input[CONF_MONITORED_CONDITIONS],
                },
            )

        default_monitored_conditions = (
            [] if self._async_current_entries() else DEFAULT_MONITORED_CONDITIONS
        )

        setup_schema = vol.Schema(
            {
                vol.Required(
                    CONF_MONITORED_CONDITIONS, default=default_monitored_conditions
                ): cv.multi_select(self._filtered_sensor_types),
            }
        )

        return self.async_show_form(
            step_id="sensors", data_schema=setup_schema, errors=self._errors
        )

    async def async_step_import(self, user_input=None):
        """Import a config entry."""
        if self._host_in_configuration_exists(user_input[CONF_HOST]):
            return self.async_abort(reason="host_exists")
        self._host = user_input[CONF_HOST]
        await self.hass.async_add_executor_job(self._check_host, self._host)
        await self.hass.async_add_executor_job(self._get_sensor, self._host)
        return await self.async_step_sensors(user_input)
