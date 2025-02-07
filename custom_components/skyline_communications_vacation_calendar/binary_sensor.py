"""Interfaces with the Integration 101 Template api sensors."""

from datetime import datetime
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
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

    def __init__(
        self, coordinator: CalendarCoordinator, entries: list[CalendarEntry]
    ) -> None:
        """Initialise sensor."""
        super().__init__(coordinator)
        self.calculate_workday(entries)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.

        coordinator: CalendarCoordinator = self.coordinator
        _LOGGER.debug("User: %s", self.coordinator.fullname)
        self.calculate_workday(coordinator.entries)
        self.async_write_ha_state()

    def calculate_workday(self, entries: list[CalendarEntry]):
        """Calculate if today is a work day or not."""

        # This needs to enumerate to true or false
        now = datetime.now()

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
        # Identifiers are what group entities into the same device.
        # If your device is created elsewhere, you can just specify the indentifiers parameter.
        # If your device connects via another device, add via_device parameter with the indentifiers of that device.
        return DeviceInfo(
            name=f"Workday Binary Sensor {self.coordinator.fullname}",
            manufacturer="DhrMaes",
            model="Workday Binary Sensor 1.0.1",
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
