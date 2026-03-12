"""The {Integration Display Name} integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import MyCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

# List of platforms to support. Uncomment and add more as needed.
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    # Platform.SWITCH,
    # Platform.LIGHT,
    # Platform.BINARY_SENSOR,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the {Integration Display Name} component."""
    # Initialize the integration's data storage
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up {Integration Display Name} from a config entry."""
    _LOGGER.debug("Setting up %s integration", DOMAIN)

    # TODO: Initialize your API client here
    # Example:
    # api = MyAPI(
    #     entry.data[CONF_HOST],
    #     entry.data[CONF_USERNAME],
    #     entry.data[CONF_PASSWORD],
    # )

    # Create the data update coordinator
    coordinator = MyCoordinator(hass, entry)

    # Fetch initial data to verify the connection works
    await coordinator.async_config_entry_first_refresh()

    # Store the coordinator in hass.data for access by platforms
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up all platforms for this integration
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading %s integration", DOMAIN)

    # Unload all platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove the config entry from hass.data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
