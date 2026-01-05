import logging
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    CONF_TEMPERATURE_UNIT,
    TEMP_UNIT_FAHRENHEIT,
    TEMP_UNIT_CELSIUS,
    TEMP_UNIT_AUTO,
    DEFAULT_TEMPERATURE_UNIT,
    TEMP_MIN_F,
    TEMP_MAX_F,
    TEMP_MIN_C,
    TEMP_MAX_C,
)
from .api import EnviApiError, EnviDeviceError, EnviAuthenticationError

_LOGGER = logging.getLogger(__name__)


def fahrenheit_to_celsius(temp_f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return round((temp_f - 32) * 5 / 9, 1)


def celsius_to_fahrenheit(temp_c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return round(temp_c * 9 / 5 + 32, 1)


class EnviHeater(ClimateEntity):
    """Representation of an Envi Heater using centralized API client."""

    _attr_has_entity_name = True
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _enable_turn_on_off_backwards_compatibility = False
    _attr_should_poll = True  # Enable polling

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client, device_id: str):
        """Initialize the heater."""
        self.hass = hass
        self.entry = entry
        self.client = client
        self.device_id = str(device_id)  # Ensure device_id is always a string
        self._attr_name = f"Envi Heater {self.device_id}"
        self._attr_unique_id = str(device_id)  # Unique ID must be a string
        self._current_temperature = None
        self._target_temperature = None
        self._attr_hvac_mode = HVACMode.OFF
        self._device_info = None
        self._attr_available = True
        
        # Temperature unit handling
        self._configured_unit = self._get_configured_unit()
        self._update_temperature_attributes()

    def _get_configured_unit(self) -> str:
        """Get the configured temperature unit from options or config."""
        # Check options first (user may have changed it after setup)
        unit = self.entry.options.get(CONF_TEMPERATURE_UNIT)
        
        # Fall back to data if not in options (legacy entries)
        if not unit:
            unit = self.entry.data.get(CONF_TEMPERATURE_UNIT, DEFAULT_TEMPERATURE_UNIT)
        
        # If 'auto', use Home Assistant's configured unit
        if unit == TEMP_UNIT_AUTO:
            ha_unit = self.hass.config.units.temperature_unit
            if ha_unit == UnitOfTemperature.CELSIUS:
                return TEMP_UNIT_CELSIUS
            else:
                return TEMP_UNIT_FAHRENHEIT
        
        return unit

    def _update_temperature_attributes(self):
        """Update temperature-related attributes based on configured unit."""
        self._configured_unit = self._get_configured_unit()
        
        if self._configured_unit == TEMP_UNIT_CELSIUS:
            self._attr_temperature_unit = UnitOfTemperature.CELSIUS
            self._attr_target_temperature_high = TEMP_MAX_C
            self._attr_target_temperature_low = TEMP_MIN_C
            self._attr_min_temp = TEMP_MIN_C
            self._attr_max_temp = TEMP_MAX_C
        else:
            self._attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
            self._attr_target_temperature_high = TEMP_MAX_F
            self._attr_target_temperature_low = TEMP_MIN_F
            self._attr_min_temp = TEMP_MIN_F
            self._attr_max_temp = TEMP_MAX_F
        
        _LOGGER.debug(
            "Temperature unit configured as %s for %s (min=%s, max=%s)",
            self._configured_unit,
            self.device_id,
            self._attr_min_temp,
            self._attr_max_temp,
        )

    def _convert_from_api(self, temp_value: float | None) -> float | None:
        """Convert temperature from API (Celsius) to configured display unit."""
        if temp_value is None:
            return None
        
        # API returns Celsius - convert to Fahrenheit if that's what user wants
        if self._configured_unit == TEMP_UNIT_FAHRENHEIT:
            return celsius_to_fahrenheit(temp_value)
        return temp_value  # Already Celsius

    def _convert_to_api(self, temp_value: float) -> float:
        """Convert temperature from configured display unit to API (Celsius)."""
        # API expects Celsius
        if self._configured_unit == TEMP_UNIT_FAHRENHEIT:
            return fahrenheit_to_celsius(temp_value)
        return temp_value  # Already Celsius

    @property
    def available(self):
        """Return if entity is available."""
        return self._attr_available

    @property
    def should_poll(self):
        """Return if polling is needed."""
        return True

    async def async_update(self):
        """Update device state from API."""
        # Check if unit configuration has changed
        self._update_temperature_attributes()
        
        try:
            data = await self.client.get_device_state(self.device_id)
            _LOGGER.debug(f"Updated device {self.device_id}: {data}")
            
            # API returns temperatures in Fahrenheit - convert if needed
            raw_ambient = data.get("ambient_temperature")
            raw_target = data.get("current_temperature")
            
            self._current_temperature = self._convert_from_api(raw_ambient)
            self._target_temperature = self._convert_from_api(raw_target)
            self._attr_hvac_mode = HVACMode.HEAT if data.get("state") == 1 else HVACMode.OFF
            self._attr_available = True
            
            _LOGGER.debug(
                f"Updated {self.device_id}: temp={self._current_temperature}°"
                f"{'C' if self._configured_unit == TEMP_UNIT_CELSIUS else 'F'}, "
                f"target={self._target_temperature}, mode={self._attr_hvac_mode}"
            )
            
        except EnviAuthenticationError as e:
            self._attr_available = False
            _LOGGER.warning("Authentication failed for %s: %s", self.device_id, str(e))
        except EnviDeviceError as e:
            self._attr_available = False
            _LOGGER.warning("Device error for %s: %s", self.device_id, str(e))
        except Exception as e:
            self._attr_available = False
            _LOGGER.warning("Failed to update %s: %s", self.device_id, str(e))

    @property
    def current_temperature(self):
        """Return current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return target temperature."""
        return self._target_temperature

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=self._attr_name,
            manufacturer="Envi",
            model="Smart Heater",
            sw_version="1.0",
        )

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        
        # Convert from configured unit to API unit (Celsius)
        api_temperature = self._convert_to_api(temperature)
        
        # Validate the temperature is within API limits (Celsius)
        if api_temperature < TEMP_MIN_C or api_temperature > TEMP_MAX_C:
            _LOGGER.error(
                f"Temperature {temperature}° out of range. "
                f"Valid range: {self._attr_min_temp}-{self._attr_max_temp}°"
            )
            return
            
        try:
            await self.client.update_device(self.device_id, {"temperature": api_temperature})
            self._target_temperature = temperature  # Store in configured unit
            _LOGGER.debug(
                f"Set temperature to {temperature}°"
                f"{'C' if self._configured_unit == TEMP_UNIT_CELSIUS else 'F'} "
                f"(API: {api_temperature}°C) for {self.device_id}"
            )
        except EnviDeviceError as e:
            _LOGGER.error(f"Device error setting temperature: {e}")
            raise
        except EnviApiError as e:
            _LOGGER.error(f"API error setting temperature: {e}")
            raise
        except Exception as e:
            _LOGGER.error(f"Unexpected error setting temperature: {e}")
            raise

    async def async_set_hvac_mode(self, hvac_mode):
        """Set HVAC mode."""
        try:
            if hvac_mode == HVACMode.HEAT:
                payload = {"state": 1}
                _LOGGER.debug(f"Turning on heater {self.device_id} with payload: {payload}")
                await self.client.update_device(self.device_id, payload)
                self._attr_hvac_mode = hvac_mode
                _LOGGER.debug(f"Turned on heater {self.device_id}")
            else:
                payload = {"state": 0}
                _LOGGER.debug(f"Turning off heater {self.device_id} with payload: {payload}")
                await self.client.update_device(self.device_id, payload)
                self._attr_hvac_mode = hvac_mode
                _LOGGER.debug(f"Turned off heater {self.device_id}")
        except EnviDeviceError as e:
            _LOGGER.error(f"Device error setting HVAC mode: {e}")
            raise
        except EnviApiError as e:
            _LOGGER.error(f"API error setting HVAC mode: {e}")
            raise
        except Exception as e:
            _LOGGER.error(f"Unexpected error setting HVAC mode: {e}")
            raise


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities
):
    """Set up all Envi heaters from a config entry."""
    client = hass.data[DOMAIN][entry.entry_id]
    
    try:
        device_ids = await client.fetch_all_device_ids()
    except Exception as e:
        _LOGGER.error("Failed to get device IDs: %s", str(e))
        return

    # Log the configured temperature unit
    temp_unit = entry.options.get(CONF_TEMPERATURE_UNIT, DEFAULT_TEMPERATURE_UNIT)
    _LOGGER.info(
        f"Found {len(device_ids)} Envi heaters: {device_ids} "
        f"(temperature unit: {temp_unit})"
    )
    
    # Create entities
    heaters = [EnviHeater(hass, entry, client, device_id) for device_id in device_ids]
    _LOGGER.info(f"Created {len(heaters)} heater entities")
    async_add_entities(heaters)
    
    # Initial update for all heaters
    for heater in heaters:
        await heater.async_update()
