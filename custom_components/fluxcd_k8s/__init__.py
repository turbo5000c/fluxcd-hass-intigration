"""The FluxCD Kubernetes integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import FluxKubernetesClient
from .const import (
    CONF_ACCESS_MODE,
    CONF_KUBECONFIG_PATH,
    CONF_LABEL_SELECTOR,
    CONF_NAMESPACE,
    CONF_SCAN_INTERVAL,
    DEFAULT_NAMESPACE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import FluxCDCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the FluxCD Kubernetes component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FluxCD Kubernetes from a config entry."""
    _LOGGER.debug("Setting up %s integration", DOMAIN)

    # Create the Kubernetes API client
    k8s_client = FluxKubernetesClient(
        access_mode=entry.data[CONF_ACCESS_MODE],
        kubeconfig_path=entry.data.get(CONF_KUBECONFIG_PATH, ""),
        namespace=entry.data.get(CONF_NAMESPACE, DEFAULT_NAMESPACE),
        label_selector=entry.data.get(CONF_LABEL_SELECTOR, ""),
    )

    try:
        await k8s_client.async_init()
    except Exception as err:
        raise ConfigEntryNotReady(
            f"Failed to initialize Kubernetes client: {err}"
        ) from err

    # Create the data update coordinator
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = FluxCDCoordinator(hass, entry, k8s_client, scan_interval)

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

    # Close the Kubernetes client and remove the config entry from hass.data
    if unload_ok:
        coordinator: FluxCDCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.k8s_client.async_close()

    return unload_ok
