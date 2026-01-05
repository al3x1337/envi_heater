import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.const import ATTR_ENTITY_ID, UnitOfTemperature

from .const import (
    DOMAIN,
    CONF_TEMPERATURE_UNIT,
    TEMP_UNIT_CELSIUS,
    TEMP_UNIT_AUTO,
    DEFAULT_TEMPERATURE_UNIT,
    TEMP_MIN_F,
    TEMP_MAX_F,
    TEMP_MIN_C,
    TEMP_MAX_C,
)
from .api import EnviApiError, EnviDeviceError

_LOGGER = logging.getLogger(__name__)


def get_temp_range_for_unit(hass: HomeAssistant, entry) -> tuple[int, int]:
    """Get temperature range based on configured unit."""
    unit = entry.options.get(CONF_TEMPERATURE_UNIT, DEFAULT_TEMPERATURE_UNIT)
    
    if unit == TEMP_UNIT_AUTO:
        ha_unit = hass.config.units.temperature_unit
        if ha_unit == UnitOfTemperature.CELSIUS:
            unit = TEMP_UNIT_CELSIUS
    
    if unit == TEMP_UNIT_CELSIUS:
        return (TEMP_MIN_C, TEMP_MAX_C)
    return (TEMP_MIN_F, TEMP_MAX_F)


async def async_setup_services(hass: HomeAssistant):
    """Set up custom services for Envi Heater integration."""
    
    async def refresh_all_heaters(call: ServiceCall):
        """Refresh all Envi heaters."""
        _LOGGER.info("Refreshing all Envi heaters")
        for entry_id, client in hass.data[DOMAIN].items():
            try:
                device_ids = await client.fetch_all_device_ids()
                for device_id in device_ids:
                    try:
                        await client.get_device_state(device_id)
                        _LOGGER.debug(f"Refreshed device {device_id}")
                    except Exception as e:
                        _LOGGER.warning(f"Failed to refresh device {device_id}: {e}")
            except Exception as e:
                _LOGGER.error(f"Failed to refresh heaters for entry {entry_id}: {e}")

    async def set_heater_schedule(call: ServiceCall):
        """Set a schedule for a heater."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        schedule_data = call.data.get("schedule", {})
        
        if not entity_id:
            _LOGGER.error("No entity ID provided")
            return
            
        _LOGGER.info(f"Setting schedule for {entity_id}: {schedule_data}")
        # Implementation would depend on Envi API schedule endpoints

    async def get_heater_status(call: ServiceCall):
        """Get detailed status of a heater."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        
        if not entity_id:
            _LOGGER.error("No entity ID provided")
            return
            
        # Find the entity and get its status
        entity = hass.states.get(entity_id)
        if not entity:
            _LOGGER.error(f"Entity {entity_id} not found")
            return
            
        _LOGGER.info(f"Status for {entity_id}: {entity.attributes}")

    async def test_connection(call: ServiceCall):
        """Test connection to Envi API."""
        _LOGGER.info("Testing connection to Envi API")
        for entry_id, client in hass.data[DOMAIN].items():
            try:
                is_connected = await client.test_connection()
                if is_connected:
                    _LOGGER.info(f"Connection test successful for entry {entry_id}")
                else:
                    _LOGGER.error(f"Connection test failed for entry {entry_id}")
            except Exception as e:
                _LOGGER.error(f"Connection test error for entry {entry_id}: {e}")

    # Register services
    hass.services.async_register(
        DOMAIN,
        "refresh_all",
        refresh_all_heaters,
        schema=vol.Schema({}),
    )
    
    # For set_schedule, we use a flexible temperature range
    # The actual validation happens in the entity based on configured unit
    hass.services.async_register(
        DOMAIN,
        "set_schedule",
        set_heater_schedule,
        schema=vol.Schema({
            vol.Required(ATTR_ENTITY_ID): cv.entity_id,
            vol.Required("schedule"): vol.Schema({
                vol.Required("enabled"): cv.boolean,
                vol.Optional("times"): vol.All(cv.ensure_list, [
                    vol.Schema({
                        vol.Required("time"): cv.time,
                        # Accept both Celsius and Fahrenheit range (5-90 covers both)
                        vol.Required("temperature"): vol.All(
                            vol.Coerce(float), 
                            vol.Range(min=5, max=90)
                        ),
                        vol.Required("enabled"): cv.boolean,
                    })
                ])
            })
        }),
    )
    
    hass.services.async_register(
        DOMAIN,
        "get_status",
        get_heater_status,
        schema=vol.Schema({
            vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        }),
    )
    
    hass.services.async_register(
        DOMAIN,
        "test_connection",
        test_connection,
        schema=vol.Schema({}),
    )

async def async_unload_services(hass: HomeAssistant):
    """Unload custom services."""
    hass.services.async_remove(DOMAIN, "refresh_all")
    hass.services.async_remove(DOMAIN, "set_schedule")
    hass.services.async_remove(DOMAIN, "get_status")
    hass.services.async_remove(DOMAIN, "test_connection")
