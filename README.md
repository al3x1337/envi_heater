# Envi Smart Heater Integration

A comprehensive Home Assistant integration for Envi Smart Heaters with enhanced reliability, error handling, and advanced features.

## 🚀 What's New in v1.1.0

### Temperature Unit Support 🌡️
- **Celsius & Fahrenheit Support**: Choose your preferred temperature unit during setup
- **Auto Detection**: Option to automatically use your Home Assistant's configured unit
- **Change Anytime**: Modify temperature unit via integration options after setup
- **Proper Conversion**: All temperature readings and settings are correctly converted

### Previous Improvements (v1.0.0)
- **Enhanced API Client**: Better error handling, token management, and retry logic
- **Improved Entity Management**: Proper device information and availability tracking
- **Custom Services**: Advanced functionality for scheduling and status monitoring
- **Better Error Recovery**: Graceful degradation and detailed error reporting
- **Production Ready**: Comprehensive logging and monitoring

### Key Features

#### 🌡️ Temperature Unit Configuration
- **Auto Mode**: Automatically uses your Home Assistant's configured unit (Celsius or Fahrenheit)
- **Manual Selection**: Explicitly choose Celsius (°C) or Fahrenheit (°F)
- **Dynamic Updates**: Changes take effect immediately
- **Proper Limits**: 
  - Fahrenheit: 50°F - 86°F
  - Celsius: 10°C - 30°C

#### 🔧 Enhanced API Client
- **Smart Token Management**: Automatic token refresh with expiration tracking
- **Retry Logic**: Exponential backoff for failed requests
- **Error Classification**: Specific error types for better debugging
- **Connection Resilience**: Handles network issues gracefully

#### 🏠 Improved Climate Entities
- **Device Information**: Proper device registry integration
- **Availability Tracking**: Real-time connection status
- **Better State Management**: Accurate temperature and mode tracking
- **Error Handling**: Specific error messages for different failure types

#### 🛠️ Custom Services
- `envi_heater.refresh_all`: Refresh all heaters
- `envi_heater.set_schedule`: Set heating schedules
- `envi_heater.get_status`: Get detailed device status

## 📋 Installation

1. Copy the `envi_heater` folder to your `custom_components` directory
2. Restart Home Assistant
3. Add the integration via the UI

## 🔧 Configuration

The integration uses the standard Home Assistant config flow:

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Envi Smart Heater"
4. Enter your Envi account credentials
5. **Select your preferred temperature unit:**
   - **Auto**: Uses your Home Assistant's configured unit
   - **Celsius (°C)**: Display temperatures in Celsius
   - **Fahrenheit (°F)**: Display temperatures in Fahrenheit
6. The integration will automatically discover your heaters

### Changing Temperature Unit After Setup

1. Go to Settings → Devices & Services
2. Find "Envi Heater" and click "Configure"
3. Select your new temperature unit
4. Click "Submit"

## 🎯 Usage

### Basic Climate Control
The integration creates climate entities for each Envi heater:
- **Temperature Control**: Set target temperature
  - Fahrenheit: 50°F - 86°F
  - Celsius: 10°C - 30°C
- **On/Off Control**: Turn heaters on/off
- **Current Temperature**: Real-time ambient temperature reading

### Custom Services

#### Refresh All Heaters
```yaml
service: envi_heater.refresh_all
```

#### Set Heater Schedule
```yaml
service: envi_heater.set_schedule
data:
  entity_id: climate.envi_heater_12345
  schedule:
    enabled: true
    times:
      - time: "08:00:00"
        temperature: 22  # Use your configured unit
        enabled: true
      - time: "18:00:00"
        temperature: 20
        enabled: true
```

#### Get Heater Status
```yaml
service: envi_heater.get_status
data:
  entity_id: climate.envi_heater_12345
```

## 🔍 Troubleshooting

### Common Issues

#### "Authentication failed"
- Check your Envi account credentials
- Ensure your account has active heaters
- Try re-authenticating via the integration settings

#### "No devices found"
- Verify you have Envi heaters in your account
- Check the Envi app to ensure heaters are online
- Restart the integration

#### "Device unavailable"
- Check your internet connection
- Verify the Envi API is accessible
- Check the Home Assistant logs for specific errors

#### Temperature displays incorrectly
- Go to integration options and verify the temperature unit setting
- Try setting to "Auto" to match your Home Assistant configuration
- Restart Home Assistant after changing the unit

### Debug Logging

Enable debug logging to see detailed information:

```yaml
logger:
  logs:
    custom_components.envi_heater: debug
```

## 🏗️ Architecture

### Components

- **API Client** (`api.py`): Handles all Envi API communication
- **Climate Platform** (`climate.py`): Home Assistant climate entities with temperature conversion
- **Config Flow** (`config_flow.py`): Setup, configuration, and options flow
- **Services** (`services.py`): Custom Home Assistant services
- **Constants** (`const.py`): Temperature limits and configuration keys

### Temperature Handling

The integration assumes the Envi API uses Fahrenheit internally:
- All API requests send temperatures in Fahrenheit
- All API responses are converted from Fahrenheit to the configured unit
- Temperature limits are enforced in both units

### Error Handling

The integration includes comprehensive error handling:

- **EnviApiError**: General API errors
- **EnviAuthenticationError**: Authentication failures
- **EnviDeviceError**: Device-specific errors

### Token Management

- Automatic token refresh before expiration
- Concurrent request protection
- Graceful fallback for authentication failures

## 🔄 Updates

The integration automatically updates device states every 30 seconds and provides immediate feedback for user actions.

## 📊 Monitoring

Monitor your integration health through:
- Home Assistant device registry
- Integration status in Settings → Devices & Services
- Debug logs for detailed operation information

## 🤝 Contributing

This integration is designed to be robust and user-friendly. If you encounter issues:

1. Check the troubleshooting section
2. Enable debug logging
3. Review the Home Assistant logs
4. Report issues with detailed logs

## 📝 Changelog

### v1.1.0
- **NEW**: Temperature unit configuration (Celsius/Fahrenheit/Auto)
- **NEW**: Options flow to change settings after setup
- **NEW**: Translations for config flow UI
- **FIX**: Fixed syntax error in JWT parsing
- **IMPROVED**: Dynamic temperature limits based on configured unit
- **IMPROVED**: Better logging with unit information

### v1.0.0
- Complete rewrite with enhanced reliability
- Added custom services
- Improved error handling
- Better device integration
- Production-ready logging

### v0.10.0
- Initial release
- Basic climate control
- Simple API integration
