"""Interfaces with the Integration 101 Template api sensors."""

from datetime import datetime
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .CalendarApi import CalendarEntry, CalendarEntryType
from .const import DOMAIN
from .coordinator import CalendarCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Binary Sensors."""
    # This gets the data update coordinator from hass.data as specified in your __init__.py
    coordinator: CalendarCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ].coordinator

    # Enumerate all the binary sensors in your data value from your DataUpdateCoordinator and add an instance of your binary sensor class
    # to a list for each one.
    # This maybe different in your specific case, depending on how your data is structured
    # binary_sensors = [
    #    ExampleBinarySensor(coordinator, device)
    #    for device in coordinator.data.devices
    #    if device.device_type == DeviceType.DOOR_SENSOR
    # ]

    binary_sensors = [
        WorkDayBinarySensor(coordinator, coordinator.data.calender_entries)
    ]

    # Create the binary sensors.
    async_add_entities(binary_sensors)


class WorkDayBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Implementation of a sensor."""

    def __init__(
        self, coordinator: CalendarCoordinator, entries: list[CalendarEntry]
    ) -> None:
        """Initialise sensor."""
        super().__init__(coordinator)
        self.entries = entries

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        self.entries: list[CalendarEntry] = (
            self.coordinator.get_calendar_entries_by_fullname(self.coordinator.fullname)
        )
        _LOGGER.debug("User: %s", self.coordinator.fullname)
        self.async_write_ha_state()

    @property
    def device_class(self) -> str:
        """Return device class."""
        # https://developers.home-assistant.io/docs/core/entity/binary-sensor#available-device-classes
        # return BinarySensorDeviceClass.DOOR
        return ""

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        # Identifiers are what group entities into the same device.
        # If your device is created elsewhere, you can just specify the indentifiers parameter.
        # If your device connects via another device, add via_device parameter with the indentifiers of that device.
        return DeviceInfo(
            name=f"Workday Sensor {self.coordinator.fullname}",
            manufacturer="DhrMaes",
            model="Workday Sensor 1.0.1",
            sw_version="1.0.1",
            identifiers={
                (
                    DOMAIN,
                    f"slc-vaction-calendar-{self.coordinator.fullname}",
                )
            },
        )

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"Workday sensor for {self.coordinator.fullname}"

    @property
    def is_on(self) -> bool | None:
        """Return if the binary sensor is on."""
        # This needs to enumerate to true or false
        now = datetime.now()

        holiday_types = [
            CalendarEntryType.Absent,
            CalendarEntryType.Public_Holiday,
            CalendarEntryType.Weekend,
        ]

        for entry in self.entries:
            print(
                f"{entry.id}: {entry.event_date} - {entry.end_date}: {entry.category}"
            )

        matching_entries = [
            entry
            for entry in self.entries
            if entry.event_date <= now <= entry.end_date
            and entry.category in holiday_types
        ]

        if matching_entries:
            return False

        return True

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
        attrs["extra_info"] = "Extra Info"
        return attrs
