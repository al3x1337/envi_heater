import logging
import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv

from .api import EnviApiClient, EnviAuthenticationError
from .const import (
    DOMAIN,
    CONF_TEMPERATURE_UNIT,
    TEMP_UNIT_FAHRENHEIT,
    TEMP_UNIT_CELSIUS,
    TEMP_UNIT_AUTO,
    DEFAULT_TEMPERATURE_UNIT,
)

_LOGGER = logging.getLogger(__name__)

# Temperature unit options for the selector
TEMP_UNIT_OPTIONS = {
    TEMP_UNIT_AUTO: "Auto (Use Home Assistant setting)",
    TEMP_UNIT_CELSIUS: "Celsius (°C)",
    TEMP_UNIT_FAHRENHEIT: "Fahrenheit (°F)",
}


class EnviHeaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Envi Heater config flow."""

    VERSION = 2  # Bumped version for new schema with temperature unit
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle user-initiated flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input["username"]
            password = user_input["password"]
            temp_unit = user_input.get(CONF_TEMPERATURE_UNIT, DEFAULT_TEMPERATURE_UNIT)

            session = async_get_clientsession(self.hass)
            client = EnviApiClient(
                session=session,
                username=username,
                password=password,
            )

            try:
                # 1) Test authentication – will raise EnviAuthenticationError on bad creds
                await client.authenticate()

                # 2) Verify device access
                device_ids = await client.fetch_all_device_ids()
                if not device_ids:
                    _LOGGER.warning(
                        "Envi login OK but no devices found for account %s", username
                    )
                    errors["base"] = "no_devices"
                else:
                    # 3) Success – store credentials and create entry
                    return self.async_create_entry(
                        title="Envi Heater",
                        data={
                            "username": username,
                            "password": password,
                        },
                        options={
                            CONF_TEMPERATURE_UNIT: temp_unit,
                        },
                    )

            except EnviAuthenticationError as e:
                _LOGGER.warning("Envi authentication failed for %s: %s", username, str(e))
                errors["base"] = "invalid_auth"

            except aiohttp.ClientError:
                _LOGGER.warning("Cannot connect to Envi API for %s", username)
                errors["base"] = "cannot_connect"

            except Exception as e:
                _LOGGER.exception("Unexpected error during Envi config flow: %s", e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): cv.string,
                    vol.Required("password"): cv.string,
                    vol.Optional(
                        CONF_TEMPERATURE_UNIT, default=DEFAULT_TEMPERATURE_UNIT
                    ): vol.In(TEMP_UNIT_OPTIONS),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data):
        """Handle re-authentication."""
        # Simple re-use of user step, you could also prefill username here if you want
        return await self.async_step_user()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return EnviHeaterOptionsFlow(config_entry)


class EnviHeaterOptionsFlow(config_entries.OptionsFlow):
    """Handle Envi Heater options flow - allows changing settings after setup."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current temperature unit setting
        current_temp_unit = self.config_entry.options.get(
            CONF_TEMPERATURE_UNIT, DEFAULT_TEMPERATURE_UNIT
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TEMPERATURE_UNIT, default=current_temp_unit
                    ): vol.In(TEMP_UNIT_OPTIONS),
                }
            ),
        )
