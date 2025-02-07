"""Interfaces with the Integration 101 Template api sensors."""

from datetime import datetime
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .CalendarApi import CalendarEntry, CalendarEntryType
from .const import CONF_ELEMENT_ID, CONF_FULLNAME, DOMAIN
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

    sensors = [DaySensor(coordinator, coordinator.entries)]

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

    calendar_options = [
        CalendarEntryType.Absent,
        CalendarEntryType.WfH,
        CalendarEntryType.Public_Holiday,
        CalendarEntryType.Weekend,
    ]

    _attr_native_unit_of_measurement = None
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: CalendarCoordinator, entries: list[CalendarEntry]
    ) -> None:
        """Initialise sensor."""
        super().__init__(coordinator)
        self._attr_options = self.options
        self.calculate_day_type(entries)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        coordinator: CalendarCoordinator = self.coordinator
        _LOGGER.debug("User: %s", coordinator.fullname)
        self.calculate_day_type(coordinator.entries)
        self.async_write_ha_state()

    def calculate_day_type(self, entries: list[CalendarEntry]):
        """Caculate the type of day based on the latest vacation entries."""

        # This needs to enumerate to true or false
        now = datetime.now()

        matching_entries = [
            entry
            for entry in entries
            if entry.event_date <= now <= entry.end_date
            and entry.category in self.calendar_options
        ]

        if matching_entries:
            self.day_type = matching_entries[0].category.name
        else:
            self.day_type = "Workday"

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
    def native_unit_of_measurement(self) -> str | None:
        """Return unit of temperature."""
        return None

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

        if self.day_type is None:
            attrs["integer_state"] = None
        else:
            attrs["integer_state"] = (
                -1
                if self.day_type == "Workday"
                else CalendarEntryType[self.day_type].value
            )

        return attrs
