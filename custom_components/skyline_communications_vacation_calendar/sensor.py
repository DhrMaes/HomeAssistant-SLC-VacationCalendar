"""Interfaces with the Integration 101 Template api sensors."""

from datetime import datetime
import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
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

    sensors = [DaySensor(coordinator, coordinator.data.calender_entries)]

    # Create the binary sensors.
    async_add_entities(sensors)


class DaySensor(CoordinatorEntity, SensorEntity):
    """Implementation of a sensor."""

    options = [
        "Workday",
        CalendarEntryType.Absent.name,
        CalendarEntryType.WfH.name,
        CalendarEntryType.Public_Holiday.name,
        CalendarEntryType.Weekend.name,
    ]

    def __init__(
        self, coordinator: CalendarCoordinator, entries: list[CalendarEntry]
    ) -> None:
        """Initialise sensor."""
        super().__init__(coordinator)
        self.day_type = self.options[0]
        self.entries = entries

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        self.entries: list[CalendarEntry] = (
            self.coordinator.get_calendar_entries_by_fullname(self.coordinator.fullname)
        )
        _LOGGER.debug("User: %s", self.coordinator.fullname)

        self._attr_options = self.options

        # This needs to enumerate to true or false
        now = datetime.now()

        day_types = [
            CalendarEntryType.Absent,
            CalendarEntryType.WfH,
            CalendarEntryType.Public_Holiday,
            CalendarEntryType.Weekend,
        ]

        matching_entries = [
            entry
            for entry in self.entries
            if entry.event_date <= now <= entry.end_date and entry.category in day_types
        ]

        if matching_entries:
            self.day_type = matching_entries[0].category.name
        else:
            self.day_type = "Workday"
        self.async_write_ha_state()

    @property
    def device_class(self) -> str:
        """Return device class."""
        # https://developers.home-assistant.io/docs/core/entity/sensor#available-device-classes
        return SensorDeviceClass.ENUM

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
    def native_value(self) -> str:
        """Return the state of the entity."""
        # Using native value and native unit of measurement, allows you to change units
        # in Lovelace and HA will automatically calculate the correct value.
        return self.day_type

    @property
    def state_class(self) -> str | None:
        """Return state class."""
        # https://developers.home-assistant.io/docs/core/entity/sensor/#available-state-classes
        return None

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
        attrs["integer_state"] = (
            -1 if self.day_type == "Workday" else CalendarEntryType(self.day_type).value
        )
        return attrs
