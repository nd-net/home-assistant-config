"""
Support for Gardena.
"""
import logging

import voluptuous as vol

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['requests']

_LOGGER = logging.getLogger(__name__)

DOMAIN = "gardena"

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)

import requests
import json

def defaults_namedtuple(name, fields):
    from collections import namedtuple
    result = namedtuple(name, fields)
    result.__new__.__defaults__ = (None,) * len(result._fields)
    return result

GardenaSession = defaults_namedtuple("GardenaSession", "token user_id refresh_token")

class Gardena:
    
    BASE_URL = "https://smart.gardena.com/sg-1"

    session = GardenaSession()
    
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def execute(self, path, data, useSession=True):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if useSession and self.session.token:
            headers["X-Session"] = self.session.token
        return requests.post(
            url=self.BASE_URL + path,
            headers=headers,
            data=json.dumps(data)
        )
        

    def login(self):
        data = {
            "sessions": {
                "email": self.username,
                "password": self.password,
            }
        }
        response = self.execute("/sessions", data, useSession=False)
        json = response.json()
        self.session = GardenaSession(**json.get("sessions", {}))


def setup(hass, config):
    """Set up the Gardena hub component"""
    _LOGGER.info("Creating new Gardena component")

    gardena = Gardena(config[DOMAIN].get(CONF_USERNAME),
                      config[DOMAIN].get(CONF_PASSWORD))
    try:
        gardena.login()
        _LOGGER.info("Logged into Gardena with %s", gardena.session)
        return True
    except BaseException as e:
        _LOGGER.error("Unable to log into Gardena: %s", repr(e))
        return False