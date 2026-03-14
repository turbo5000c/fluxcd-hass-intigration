"""Sensor platform for FluxCD Kubernetes resources."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FLUX_RESOURCES, STATE_UNKNOWN
from .coordinator import FluxCDCoordinator
from .models import FluxResource, _get_condition_flag

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

# Map resource kind to its display name for device naming
_KIND_TO_RESOURCE_TYPE: dict[str, str] = {
    crd["kind"]: crd["resource_type"] for crd in FLUX_RESOURCES
}

# Kind-specific icons for the main status sensor
_KIND_ICONS: dict[str, str] = {
    "GitRepository": "mdi:git",
    "HelmRepository": "mdi:package-variant-closed",
    "HelmChart": "mdi:chart-box-outline",
    "HelmRelease": "mdi:package-variant",
    "Kustomization": "mdi:puzzle-outline",
    "OCIRepository": "mdi:docker",
    "Bucket": "mdi:bucket-outline",
    "FluxInstance": "mdi:kubernetes",
    "ResourceSet": "mdi:layers-outline",
    "ArtifactGenerator": "mdi:file-code-outline",
    "ExternalArtifact": "mdi:download-box-outline",
    "ResourceSetInputProvider": "mdi:database-import-outline",
}

# Diagnostic sensors created for every FluxCD resource kind.
# Each entry: (attr_key, display_name_suffix, mdi_icon)
_COMMON_DIAGNOSTIC_SENSORS: list[tuple[str, str, str]] = [
    ("ready_condition", "Ready Condition", "mdi:check-circle-outline"),
    ("observed_generation", "Observed Generation", "mdi:counter"),
]

# Additional diagnostic sensors per resource kind
_KIND_EXTRA_DIAGNOSTIC_SENSORS: dict[str, list[tuple[str, str, str]]] = {
    "GitRepository": [
        ("interval", "Interval", "mdi:timer-outline"),
        ("artifact_revision", "Artifact Revision", "mdi:tag-outline"),
    ],
    "HelmRepository": [
        ("interval", "Interval", "mdi:timer-outline"),
        ("artifact_revision", "Artifact Revision", "mdi:tag-outline"),
    ],
    "HelmChart": [
        ("interval", "Interval", "mdi:timer-outline"),
        ("artifact_revision", "Artifact Revision", "mdi:tag-outline"),
    ],
    "OCIRepository": [
        ("interval", "Interval", "mdi:timer-outline"),
        ("artifact_revision", "Artifact Revision", "mdi:tag-outline"),
    ],
    "Bucket": [
        ("interval", "Interval", "mdi:timer-outline"),
        ("artifact_revision", "Artifact Revision", "mdi:tag-outline"),
    ],
    "HelmRelease": [
        ("interval", "Interval", "mdi:timer-outline"),
        ("last_applied_revision", "Last Applied Revision", "mdi:tag-outline"),
    ],
    "Kustomization": [
        ("interval", "Interval", "mdi:timer-outline"),
        ("last_applied_revision", "Last Applied Revision", "mdi:tag-outline"),
    ],
    "FluxInstance": [
        ("last_applied_revision", "Last Applied Revision", "mdi:tag-outline"),
    ],
    "ResourceSet": [
        ("interval", "Interval", "mdi:timer-outline"),
    ],
    "ArtifactGenerator": [
        ("interval", "Interval", "mdi:timer-outline"),
        ("artifact_revision", "Artifact Revision", "mdi:tag-outline"),
    ],
    "ExternalArtifact": [
        ("interval", "Interval", "mdi:timer-outline"),
        ("artifact_revision", "Artifact Revision", "mdi:tag-outline"),
    ],
    "ResourceSetInputProvider": [],
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FluxCD sensor entities from a config entry.

    Creates one primary status sensor and several diagnostic sensors for
    each FluxCD resource discovered in the Kubernetes cluster.
    """
    coordinator: FluxCDCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors: list[SensorEntity] = []
    if coordinator.data:
        for resources in coordinator.data.values():
            for resource in resources:
                sensors.append(FluxCDResourceSensor(coordinator, entry, resource))
                sensors.extend(
                    _create_diagnostic_sensors(coordinator, entry, resource)
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
    """Check for new FluxCD resources and add entities for them.

    Also ensures that the kind device exists for any newly discovered resource
    kind, in case that kind had no resources during the initial setup.
    """
    if not coordinator.data:
        return

    # Ensure kind devices exist for any kind that now has resources.
    # This covers the case where a resource kind has no data at setup time
    # (so its kind device was skipped) but resources appear later.
    device_reg = dr.async_get(coordinator.hass)
    for kind, resources in coordinator.data.items():
        if not resources:
            continue
        resource_type = _KIND_TO_RESOURCE_TYPE.get(kind, kind)
        device_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"{entry.entry_id}_{kind}")},
            name=resource_type,
            manufacturer="FluxCD",
            model=f"FluxCD {kind}",
        )

    new_sensors: list[SensorEntity] = []
    for resources in coordinator.data.values():
        for resource in resources:
            unique_id = _build_unique_id(entry.entry_id, resource)
            if unique_id not in known_ids:
                known_ids.add(unique_id)
                new_sensors.append(
                    FluxCDResourceSensor(coordinator, entry, resource)
                )
                for diag in _create_diagnostic_sensors(coordinator, entry, resource):
                    if diag.unique_id not in known_ids:
                        known_ids.add(diag.unique_id)
                        new_sensors.append(diag)

    if new_sensors:
        async_add_entities(new_sensors)


def _build_unique_id(entry_id: str, resource: FluxResource) -> str:
    """Build a unique ID for a FluxCD resource sensor."""
    return f"{entry_id}_{resource.kind}_{resource.namespace}_{resource.name}"


def _build_device_info(entry_id: str, resource: FluxResource) -> dict[str, Any]:
    """Build device_info for a single FluxCD resource instance.

    Each resource gets its own HA device (e.g. "traefik/traefik") that is
    nested under the shared kind device (e.g. "Helm Repositories"), which in
    turn is nested under the category device (Sources / Deployments).

    The full hierarchy registered in __init__.py is:
        Hub → Category (Sources/Deployments) → Kind (Helm Repositories) → Resource

    Resource identifiers include namespace and name so that each Kubernetes
    resource maps to a stable, unique device.  If a resource is renamed in
    the cluster, HA will treat it as a new device (the old one becomes
    orphaned), which is the expected behaviour for k8s-backed integrations.
    """
    kind = resource.kind
    resource_type = _KIND_TO_RESOURCE_TYPE.get(kind, kind)

    return {
        "identifiers": {
            (DOMAIN, f"{entry_id}_{kind}_{resource.namespace}_{resource.name}")
        },
        "name": f"{resource.namespace}/{resource.name}",
        "manufacturer": "FluxCD",
        "model": resource_type,
        # Kind devices (e.g. "Helm Repositories") are registered in __init__.py;
        # resource devices link to them to maintain the full hierarchy.
        "via_device": (DOMAIN, f"{entry_id}_{kind}"),
    }


def _create_diagnostic_sensors(
    coordinator: FluxCDCoordinator,
    entry: ConfigEntry,
    resource: FluxResource,
) -> list[FluxCDDiagnosticSensor]:
    """Create diagnostic sensor entities for a FluxCD resource."""
    defs: list[tuple[str, str, str]] = list(_COMMON_DIAGNOSTIC_SENSORS)
    defs.extend(_KIND_EXTRA_DIAGNOSTIC_SENSORS.get(resource.kind, []))
    return [
        FluxCDDiagnosticSensor(coordinator, entry, resource, attr_key, name, icon)
        for attr_key, name, icon in defs
    ]


class FluxCDResourceSensor(CoordinatorEntity[FluxCDCoordinator], SensorEntity):
    """Sensor entity representing a single FluxCD resource.

    The primary state is the ready status (ready, not_ready, progressing,
    suspended, or unknown).  Extra state attributes expose the most useful
    per-resource fields at a glance.  Detailed diagnostic data is split out
    into separate FluxCDDiagnosticSensor entities so that it appears in the
    "Diagnostic" section of the HA device page.

    Because has_entity_name is True, HA automatically prefixes this entity
    with the device name ("traefik/traefik") in global views while showing
    just "Status" on the device page — matching the Portainer-style layout.
    """

    _attr_has_entity_name = True

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
        self._attr_name = "Status"
        self._attr_icon = _KIND_ICONS.get(resource.kind, "mdi:kubernetes")
        self._attr_device_info = _build_device_info(entry.entry_id, resource)

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
        """Return primary state attributes for the FluxCD resource."""
        resource = self._find_resource()
        if resource is None:
            return {}

        attrs: dict[str, Any] = {
            "category": resource.category.lower(),
            "kind": resource.kind,
            "namespace": resource.namespace,
            "resource_name": resource.name,
            "suspended": resource.suspend,
            "reason": resource.reason,
            "message": resource.message,
            "reconcile_time": resource.reconcile_time,
        }

        # Add kind-specific primary attributes (source, chart, version, summary, …)
        attrs.update(resource.extra_attributes)

        return attrs


class FluxCDDiagnosticSensor(CoordinatorEntity[FluxCDCoordinator], SensorEntity):
    """Diagnostic sensor exposing a single low-level attribute of a FluxCD resource.

    These sensors appear under the "Diagnostic" section of the HA device page,
    keeping the primary sensor uncluttered while still surfacing useful data.

    Because has_entity_name is True, HA prefixes the entity with the device
    name in global views (e.g. "traefik/traefik Ready Condition") while
    showing just "Ready Condition" on the device page.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FluxCDCoordinator,
        entry: ConfigEntry,
        resource: FluxResource,
        attr_key: str,
        display_name: str,
        icon: str,
    ) -> None:
        """Initialize the diagnostic sensor."""
        resource_unique_id = _build_unique_id(entry.entry_id, resource)
        super().__init__(coordinator, context=resource_unique_id)

        self._resource_kind = resource.kind
        self._resource_name = resource.name
        self._resource_namespace = resource.namespace
        self._attr_key = attr_key

        self._attr_unique_id = f"{resource_unique_id}_{attr_key}"
        self._attr_name = display_name
        self._attr_icon = icon
        self._attr_device_info = _build_device_info(entry.entry_id, resource)

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
    def native_value(self) -> Any:
        """Return the value of the diagnostic attribute."""
        resource = self._find_resource()
        if resource is None:
            return None

        # Special-cased fields that live on the model or are derived from conditions
        if self._attr_key == "observed_generation":
            return resource.observed_generation
        if self._attr_key == "ready_condition":
            return _get_condition_flag(resource.conditions, "Ready")
        if self._attr_key == "artifact_in_storage":
            return _get_condition_flag(resource.conditions, "ArtifactInStorage")

        # All other diagnostic attributes come from the diagnostic_attributes dict
        return resource.diagnostic_attributes.get(self._attr_key)

    @property
    def available(self) -> bool:
        """Return True if the coordinator has data."""
        return self.coordinator.last_update_success
