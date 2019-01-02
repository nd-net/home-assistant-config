"""
Support for Gardena.
"""
import logging

import voluptuous as vol

from homeassistant.const import (
    ATTR_BATTERY_LEVEL, CONF_USERNAME, CONF_PASSWORD)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
import homeassistant.helpers.config_validation as cv

from homeassistant.helpers.icon import icon_for_battery_level


REQUIREMENTS = ['https://github.com/nd-net/Gardena-python/archive/master.zip#Gardena-python==0.0.1']

from gardena import *

_LOGGER = logging.getLogger(__name__)

DOMAIN = "gardena"

DATA_GARDENA = "gardena"

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up the Gardena hub component"""
    _LOGGER.info("Creating new Gardena component")
    component = EntityComponent(_LOGGER, DOMAIN, hass)

    gardena_hub = Hub(config[DOMAIN].get(CONF_USERNAME),
                  config[DOMAIN].get(CONF_PASSWORD))
    try:
        gardena_hub.login()
        _LOGGER.info("Logged into Gardena with %s", gardena_hub.session)
    except BaseException as e:
        _LOGGER.error("Unable to log into Gardena: %s", repr(e))
        return False
    
    devices = []
    for location in gardena_hub.retrieve_locations():
        for device in gardena_hub.retrieve_devices(location):
            ent = GardenaEntity(hass, gardena_hub, location, device)
            devices.append(ent)
    if not devices:
        return False
    
    component.add_entities(devices)
    
    return True

class GardenaEntity(Entity):
    
    def __init__(self, hass, hub, location, device):
        self.hass = hass
        self.hub = hub
        self.location = location
        self.device = device
    
    def find_property(self, ability_name, property_name):
        for ability in self.device.abilities:
            if ability.name != ability_name:
                continue
            for property in ability.properties:
                if property.name == property_name:
                    return property
        return None
    
    @property
    def entity_id(self):
        return "gardena.{device.name}".format(device=self.device)
    
    @property
    def name(self):
        return self.device.name
    
    @property
    def state(self):
        prop = self.find_property(Abilities.mower, Properties.status)
        return prop.value if prop else self.device.device_state
    
    @property
    def battery_level(self):
        prop = self.find_property(Abilities.battery, Properties.level)
        return prop.value if prop else None
    
    @property
    def battery_icon(self):
        """Return the battery icon for the vacuum cleaner."""
        state = self.state
        charging = bool(state == "ok_charging" or state.startswith("parked_"))

        return icon_for_battery_level(
            battery_level=self.battery_level, charging=charging)
    
    @property
    def state_attributes(self):
        result = {}
        for ability in self.device.abilities:
            for prop in ability.properties:
                key = "{ability.name}_{property.name}".format(ability=ability, property=prop)
                if isinstance(prop.value, dict):
                    for k, v in prop.value.items():
                        result[key + "_" + k] = v
                else:
                    result[key] = prop.value
        
        if self.battery_level is not None:
            result[ATTR_BATTERY_LEVEL] = self.battery_level
        
        return result