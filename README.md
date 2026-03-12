# Home Assistant Integration Template

A complete template repository for creating custom Home Assistant integrations following official Home Assistant developer documentation and best practices.

## Quick Start

1. **Use this template**: Click "Use this template" button on GitHub to create your own repository
2. **Clone your repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_INTEGRATION_NAME.git
   cd YOUR_INTEGRATION_NAME
   ```
3. **Replace placeholders**: Search and replace the following placeholders throughout the codebase:
   - `{INTEGRATION_NAME}` → Your integration domain (lowercase, underscores, e.g., `my_device`)
   - `{Integration Display Name}` → Your integration friendly name (e.g., `My Device`)
   - `@turbo5000c` → Your GitHub username
4. **Rename the integration directory**:
   ```bash
   mv custom_components/\{INTEGRATION_NAME\} custom_components/your_integration_name
   ```
5. **Implement your integration logic**: Follow the TODO comments in each file

## File Structure

```
.
├── README.md                          # This file
├── .gitignore                         # Python and IDE ignores
├── .github/
│   └── ISSUE_TEMPLATE/
│       └── bug_report.md              # Bug report template
└── custom_components/
    └── {INTEGRATION_NAME}/            # Your integration directory
        ├── __init__.py                # Main integration setup
        ├── manifest.json              # Integration metadata
        ├── const.py                   # Constants and configuration keys
        ├── config_flow.py             # Configuration UI flow
        ├── coordinator.py             # Data update coordinator
        ├── sensor.py                  # Example sensor platform
        ├── services.yaml              # Service definitions
        ├── strings.json               # UI strings for config flow
        └── translations/
            └── en.json                # English translations
```

## Usage Guide

### Creating Your Integration

Each file in `custom_components/{INTEGRATION_NAME}/` contains detailed comments and TODO markers to guide you through the implementation:

#### 1. manifest.json
- Define your integration's metadata
- Set dependencies and requirements
- Configure integration type and IoT class

#### 2. __init__.py
- Implement `async_setup_entry()` to initialize your integration
- Implement `async_unload_entry()` to clean up resources
- Add platforms (sensor, switch, light, etc.) as needed

#### 3. const.py
- Define constants like DOMAIN, configuration keys, and default values
- Keep all magic strings and numbers here

#### 4. config_flow.py
- Implement the configuration UI flow
- Add validation for user input
- Handle connection errors gracefully

#### 5. coordinator.py
- Implement the `DataUpdateCoordinator` to fetch data from your device/API
- Handle API calls and error handling
- Set appropriate update intervals

#### 6. sensor.py (Example Platform)
- Create entity classes for your sensors
- Implement properties like `native_value`, `device_class`, etc.
- Add more platform files (switch.py, light.py) as needed

#### 7. services.yaml & strings.json
- Define custom services your integration provides
- Add UI strings for configuration and error messages

### Testing Your Integration

1. **Copy to Home Assistant**:
   ```bash
   cp -r custom_components/{INTEGRATION_NAME} /path/to/homeassistant/custom_components/
   ```

2. **Restart Home Assistant**

3. **Add Integration**:
   - Go to Settings → Devices & Services
   - Click "+ ADD INTEGRATION"
   - Search for your integration name
   - Follow the configuration flow

4. **Check Logs**:
   ```bash
   tail -f /path/to/homeassistant/home-assistant.log | grep {INTEGRATION_NAME}
   ```

### Development Tips

- Use proper type hints throughout your code
- Follow async/await patterns for all I/O operations
- Use the coordinator pattern to avoid polling each entity individually
- Implement proper error handling and logging
- Test with different error scenarios (network failures, invalid credentials, etc.)
- Follow Home Assistant's coding standards: https://developers.home-assistant.io/docs/development_guidelines

## Features Included

✅ Complete integration structure following HA best practices  
✅ Configuration flow with validation and error handling  
✅ DataUpdateCoordinator for efficient data fetching  
✅ Example sensor platform  
✅ Service definitions  
✅ Proper logging setup  
✅ Type hints and modern Python syntax (3.11+)  
✅ Comprehensive TODO comments for easy customization  
✅ Translations support  

## Requirements

- Home Assistant 2024.1.0 or newer
- Python 3.11 or newer

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This template is provided as-is for creating Home Assistant integrations.

## Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Integration Development](https://developers.home-assistant.io/docs/creating_integration_manifest)
- [Configuration Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler)
- [Entity Documentation](https://developers.home-assistant.io/docs/core/entity)