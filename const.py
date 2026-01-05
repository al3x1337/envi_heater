DOMAIN = "envi_heater"
OPTIONS_KEY = "envi_heater_options"

# Temperature unit configuration
CONF_TEMPERATURE_UNIT = "temperature_unit"
TEMP_UNIT_FAHRENHEIT = "fahrenheit"
TEMP_UNIT_CELSIUS = "celsius"
TEMP_UNIT_AUTO = "auto"  # Use Home Assistant's configured unit

# Default temperature unit
DEFAULT_TEMPERATURE_UNIT = TEMP_UNIT_AUTO

# Temperature limits - API uses CELSIUS internally (5°C to 30°C)
# Fahrenheit equivalents: 41°F to 86°F
TEMP_MIN_C = 5
TEMP_MAX_C = 30
TEMP_MIN_F = 41  # 5°C in Fahrenheit
TEMP_MAX_F = 86  # 30°C in Fahrenheit

# API always expects Celsius
API_TEMP_UNIT = "celsius"
