"""The FluxCD Kubernetes integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

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
    FLUX_RESOURCES,
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

    # Register kind devices in the device registry so that per-resource
    # sensor entities are grouped hierarchically.  Only kinds that actually
    # have resources are registered; empty kinds are skipped so they don't
    # add noise to the integration's device list.
    #
    # Resulting layout in Settings → Devices & Services:
    #   Git Repositories          ← kind device (top-level)
    #     └── flux-system/flux-system   ← resource device
    #     └── code-server/code-server
    #   Helm Repositories
    #     └── traefik/traefik
    #     └── bitnami/bitnami
    #   ...
    device_reg = dr.async_get(hass)
    populated_kinds: set[str] = {
        kind
        for kind, resources in (coordinator.data or {}).items()
        if resources
    }
    for flux_crd in FLUX_RESOURCES:
        kind = flux_crd["kind"]
        if kind not in populated_kinds:
            continue
        resource_type = flux_crd["resource_type"]
        device_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"{entry.entry_id}_{kind}")},
            name=resource_type,
            manufacturer="FluxCD",
            model=f"FluxCD {kind}",
            # No via_device: kind devices appear at the top level so users
            # can navigate directly into Git Repositories / Helm Repositories
            # etc. without an intermediate hub or category node.
        )

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
