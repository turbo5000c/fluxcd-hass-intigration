"""Sensor platform for FluxCD Kubernetes resources."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CATEGORY_SOURCES, DOMAIN, FLUX_RESOURCES, STATE_UNKNOWN
from .coordinator import FluxCDCoordinator
from .models import FluxResource

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

# Map resource kind to its display name for device naming
_KIND_TO_RESOURCE_TYPE: dict[str, str] = {
    crd["kind"]: crd["resource_type"] for crd in FLUX_RESOURCES
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FluxCD sensor entities from a config entry.

    Creates one sensor entity for each FluxCD resource discovered
    in the Kubernetes cluster.
    """
    coordinator: FluxCDCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors: list[FluxCDResourceSensor] = []
    if coordinator.data:
        for resources in coordinator.data.values():
            for resource in resources:
                sensors.append(
                    FluxCDResourceSensor(coordinator, entry, resource)
                )

    async_add_entities(sensors)

    # Track which unique IDs have already been added as entities
    known_ids: set[str] = {s.unique_id for s in sensors if s.unique_id}

    # Register a listener to add new entities when resources are discovered
    entry.async_on_unload(
        coordinator.async_add_listener(
            partial(
                _async_check_new_entities,
                coordinator,
                entry,
                async_add_entities,
                known_ids,
            )
        )
    )


def _async_check_new_entities(
    coordinator: FluxCDCoordinator,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    known_ids: set[str],
) -> None:
    """Check for new FluxCD resources and add entities for them."""
    if not coordinator.data:
        return

    new_sensors: list[FluxCDResourceSensor] = []
    for resources in coordinator.data.values():
        for resource in resources:
            unique_id = _build_unique_id(entry.entry_id, resource)
            if unique_id not in known_ids:
                known_ids.add(unique_id)
                new_sensors.append(
                    FluxCDResourceSensor(coordinator, entry, resource)
                )

    if new_sensors:
        async_add_entities(new_sensors)


def _build_unique_id(entry_id: str, resource: FluxResource) -> str:
    """Build a unique ID for a FluxCD resource sensor."""
    return f"{entry_id}_{resource.kind}_{resource.namespace}_{resource.name}"


class FluxCDResourceSensor(CoordinatorEntity[FluxCDCoordinator], SensorEntity):
    """Sensor entity representing a single FluxCD resource.

    The primary state is the ready status (ready, not_ready, unknown).
    Extra state attributes contain kind-specific details extracted from
    the Kubernetes custom resource.
    """

    def __init__(
        self,
        coordinator: FluxCDCoordinator,
        entry: ConfigEntry,
        resource: FluxResource,
    ) -> None:
        """Initialize the FluxCD resource sensor."""
        super().__init__(
            coordinator,
            context=_build_unique_id(entry.entry_id, resource),
        )

        self._resource_kind = resource.kind
        self._resource_name = resource.name
        self._resource_namespace = resource.namespace

        self._attr_unique_id = _build_unique_id(entry.entry_id, resource)
        self._attr_name = f"{resource.name} - {resource.namespace}"
        self._attr_icon = "mdi:kubernetes"

        # Each entity belongs to a resource type device (e.g., "Git Repositories")
        # which is a child of a category device (Sources or Deployments).
        # The device hierarchy is: Hub → Category → Resource Type → Entity
        # Device identifiers use kind (e.g., "entry_id_GitRepository") for
        # resource type devices, and category (e.g., "entry_id_Sources") for
        # category devices.
        kind = resource.kind
        category = resource.category or CATEGORY_SOURCES
        resource_type = _KIND_TO_RESOURCE_TYPE.get(kind, kind)

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_{kind}")},
            "name": resource_type,
            "manufacturer": "FluxCD",
            "model": f"FluxCD {kind}",
            "via_device": (DOMAIN, f"{entry.entry_id}_{category}"),
        }

    def _find_resource(self) -> FluxResource | None:
        """Find this sensor's resource in the coordinator data."""
        if not self.coordinator.data:
            return None
        resources = self.coordinator.data.get(self._resource_kind, [])
        for res in resources:
            if (
                res.name == self._resource_name
                and res.namespace == self._resource_namespace
            ):
                return res
        return None

    @property
    def native_value(self) -> str:
        """Return the ready status of the FluxCD resource."""
        resource = self._find_resource()
        if resource is None:
            return STATE_UNKNOWN
        return resource.ready_status

    @property
    def available(self) -> bool:
        """Return True if the coordinator has data."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes for the FluxCD resource.

        Includes common fields (kind, namespace, suspend, conditions)
        and kind-specific attributes (url, chart, path, etc.).
        """
        resource = self._find_resource()
        if resource is None:
            return {}

        attrs: dict[str, Any] = {
            "category": resource.category,
            "kind": resource.kind,
            "namespace": resource.namespace,
            "resource_name": resource.name,
            "suspend": resource.suspend,
            "message": resource.message,
            "reason": resource.reason,
            "last_reconcile_time": resource.last_reconcile_time,
            "observed_generation": resource.observed_generation,
            "conditions": [
                {
                    "type": c.type,
                    "status": c.status,
                    "reason": c.reason,
                    "message": c.message,
                    "last_transition_time": c.last_transition_time,
                }
                for c in resource.conditions
            ],
        }

        # Add kind-specific extra attributes
        attrs.update(resource.extra_attributes)

        return attrs
