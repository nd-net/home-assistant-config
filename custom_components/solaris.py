"""
Support for reading data of a Rotex Solaris RPS3 data from a serial port
"""
import logging
import json

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME, CONF_VALUE_TEMPLATE, EVENT_HOMEASSISTANT_STOP)
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_NAME, TEMP_FAHRENHEIT
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.util.temperature import celsius_to_fahrenheit

REQUIREMENTS = ['pyserial-asyncio==0.4']

_LOGGER = logging.getLogger(__name__)

CONF_SERIAL_PORT = 'serial_port'
CONF_BAUDRATE = 'baudrate'

DEFAULT_NAME = "solaris"
DEFAULT_BAUDRATE = 19200

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SERIAL_PORT): cv.string,
    vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE):
        cv.positive_int,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

LINE_MAPPING = [
    ('unknown_1', None),
    ('unknown_2', None),
    ('pump_1', '%'),
    ('pump_2', 'bool'),
    ('collector_temperature', '°C'),
    ('return_flow_temperature', '°C'),
    ('storage_temperature', '°C'),
    ('flow_temperature', '°C'),
    ('flow', 'l/min'),
    ('status', None),
    ('momentary_output', 'W')
]

async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the Solaris sensor platform."""
    name = config.get(CONF_NAME)
    port = config.get(CONF_SERIAL_PORT)
    baudrate = config.get(CONF_BAUDRATE)
    temp_unit = hass.config.units.temperature_unit

    sensor = SerialSensor(name, port, baudrate, value_template)
    sensor_handler = await hass.async_add_job(SolarisHandler, hass, port, baudrate)
    
    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP, sensor_handler.stop_serial_read())
    async_add_entities([sensor], True)


class SolarisHandler:
    """Implement Rotex Solaris communication."""

    def __init__(self, hass, port, baudrate):
        """Initialize the sensor handler"""
        self._port = port
        self._hass = hass
        self._baudrate = baudrate
        self._serial_loop_task = self.hass.loop.create_task(
            self.serial_read(self._port, self._baudrate))

    async def serial_read(self, device, rate, **kwargs):
        """Read the data from the port."""
        import serial_asyncio
        reader, _ = await serial_asyncio.open_serial_connection(
            url=device, baudrate=rate, **kwargs)
        while True:
            line = await reader.readline()
            line = line.decode('utf-8').strip()
            self.data = line.split(';')
            self.async_schedule_update_ha_state()

class SerialSensor(Entity):
    """Representation of a Serial sensor."""

    def __init__(self, name, port, baudrate, value_template):
        """Initialize the Serial sensor."""
        self._name = name
        self._state = None
        self._port = port
        self._baudrate = baudrate
        self._serial_loop_task = None


    async def serial_read(self, device, rate, **kwargs):
        """Read the data from the port."""
        import serial_asyncio
        reader, _ = await serial_asyncio.open_serial_connection(
            url=device, baudrate=rate, **kwargs)
        while True:
            line = await reader.readline()
            line = line.decode('utf-8').strip()

            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    self._attributes = data
            except ValueError:
                pass

            if self._template is not None:
                line = self._template.async_render_with_possible_json_value(
                    line)

            _LOGGER.debug("Received: %s", line)
            self._state = line
            self.async_schedule_update_ha_state()

    async def stop_serial_read(self):
        """Close resources."""
        if self._serial_loop_task:
            self._serial_loop_task.cancel()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def device_state_attributes(self):
        """Return the attributes of the entity (if any JSON present)."""
        return self._attributes

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state