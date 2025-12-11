"""Skyline Communications Vacation Calendar."""

from datetime import datetime
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
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
    coordinator: CalendarCoordinator

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
        _LOGGER.debug("User: %s", self.coordinator.fullname)
        self.calculate_day_type(self.coordinator.entries)
        self.async_write_ha_state()

    def calculate_day_type(self, entries: list[CalendarEntry]):
        """Caculate the type of day based on the latest vacation entries."""

        # This needs to enumerate to true or false
        now = datetime.now().astimezone()

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
