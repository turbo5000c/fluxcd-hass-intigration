"""Sensor platform for {Integration Display Name}."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MyCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: MyCoordinator = hass.data[DOMAIN][entry.entry_id]

    # TODO: Add your sensors here
    # Create a list of sensor entities
    sensors = [
        ExampleSensor(coordinator, entry),
        # Add more sensors as needed
    ]

    async_add_entities(sensors)


class ExampleSensor(CoordinatorEntity[MyCoordinator], SensorEntity):
    """Representation of an example sensor."""

    def __init__(self, coordinator: MyCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        # Set the unique ID for the entity
        self._attr_unique_id = f"{entry.entry_id}_example_sensor"
        
        # Set the entity name
        self._attr_name = "Example Sensor"
        
        # TODO: Set the device class, state class, and unit of measurement
        # Uncomment and modify as needed:
        # self._attr_device_class = SensorDeviceClass.TEMPERATURE
        # self._attr_state_class = SensorStateClass.MEASUREMENT
        # self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        
        # Set the device info to group entities under a device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Example Manufacturer",
            "model": "Example Model",
            # "sw_version": "1.0.0",
        }

    @property
    def native_value(self) -> float | int | str | None:
        """Return the state of the sensor."""
        # TODO: Return the sensor value from the coordinator data
        # Example:
        # return self.coordinator.data.get("example_sensor")
        
        # Placeholder return value
        return self.coordinator.data.get("example_sensor", 0)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success
