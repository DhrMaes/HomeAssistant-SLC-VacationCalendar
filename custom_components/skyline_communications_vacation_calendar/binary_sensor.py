"""Skyline Communications Vacation Calendar."""

from datetime import datetime
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    DOMAIN_METRICS_URL,
    MANUFACTURER_NAME,
    MODEL_NAME,
    SERVICE_NAME,
)
from .coordinator import CalendarCoordinator
from .skyline.calendar_api import CalendarEntry, CalendarEntryType

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Binary Sensors."""
    coordinator: CalendarCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    binary_sensors = [WorkDayBinarySensor(coordinator, coordinator.entries)]

    # Create the binary sensors.
    async_add_entities(binary_sensors)


class WorkDayBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Implementation of a sensor."""

    holiday_types = [
        CalendarEntryType.Absent,
        CalendarEntryType.Public_Holiday,
        CalendarEntryType.Weekend,
    ]
    coordinator: CalendarCoordinator

    def __init__(
        self, coordinator: CalendarCoordinator, entries: list[CalendarEntry]
    ) -> None:
        """Initialise sensor."""
        super().__init__(coordinator)
        self.calculate_workday(entries)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        _LOGGER.debug("User: %s", self.coordinator.fullname)
        self.calculate_workday(self.coordinator.entries)
        self.async_write_ha_state()

    def calculate_workday(self, entries: list[CalendarEntry]):
        """Calculate if today is a work day or not."""

        # This needs to enumerate to true or false
        now = datetime.now().astimezone()

        matching_entries = [
            entry
            for entry in entries
            if entry.event_date <= now <= entry.end_date
            and entry.category in self.holiday_types
        ]

        if matching_entries:
            self.is_workday = False
        else:
            self.is_workday = True

    @property
    def device_class(self) -> str | None:
        """Return device class."""
        # https://developers.home-assistant.io/docs/core/entity/binary-sensor#available-device-classes
        # return BinarySensorDeviceClass.DOOR
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            name=SERVICE_NAME,
            manufacturer=MANUFACTURER_NAME,
            model=MODEL_NAME,
            sw_version=None,
            identifiers={
                (
                    DOMAIN,
                    f"slc-vaction-calendar-{self.coordinator.fullname}",
                )
            },
            configuration_url=DOMAIN_METRICS_URL,
        )

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"Workday binary sensor for {self.coordinator.fullname}"

    @property
    def is_on(self) -> bool | None:
        """Return if the binary sensor is on."""
        return self.is_workday

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        # All entities must have a unique id.  Think carefully what you want this to be as
        # changing it later will cause HA to create new entities.
        return f"{DOMAIN}-workday-{self.coordinator.fullname}"

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        # Add any additional attributes you want on your sensor.
        attrs = {}
        attrs["friendly_state"] = "workday" if self.is_workday else "day off"
        return attrs
