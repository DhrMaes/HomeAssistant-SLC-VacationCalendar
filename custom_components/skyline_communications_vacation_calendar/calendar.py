"""Skyline Communications Vacation Calendar."""

from datetime import date, datetime, time, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .config_flow import default_calendar_entity_foreach_type, default_calendar_types
from .const import (
    CONF_OPTION_CALENDAR_ENTITY_FOREACH_TYPE,
    CONF_OPTION_CALENDAR_TYPES,
    DOMAIN,
    DOMAIN_METRICS_URL,
    MANUFACTURER_NAME,
    MODEL_NAME,
    SERVICE_NAME,
)
from .coordinator import CalendarCoordinator
from .skyline.calendar_api import (
    CalendarEntry,
    CalendarEntryType,
    get_calendar_type_display_value,
    to_calendar_entry_types,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Skyline Communications Vacation Calendar entry."""
    coordinator: CalendarCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    calendar_entity_per_type: bool = config_entry.options.get(
        CONF_OPTION_CALENDAR_ENTITY_FOREACH_TYPE, default_calendar_entity_foreach_type
    )
    entities: list[SLCVacationCalendarEntity] = []
    calendar_types: list[CalendarEntryType] = to_calendar_entry_types(
        config_entry.options.get(CONF_OPTION_CALENDAR_TYPES, default_calendar_types)
    )

    if calendar_entity_per_type:
        for calendar_type in calendar_types:
            calendar_item_to_add = SLCVacationCalendarEntity(
                f"{get_calendar_type_display_value(calendar_type)} Calendar - {coordinator.fullname}",
                f"{calendar_type}-{config_entry.entry_id}",
                [calendar_type],
                coordinator,
            )
            entities.append(calendar_item_to_add)
    else:
        calendar_item_to_add = SLCVacationCalendarEntity(
            f"Calendar - {coordinator.fullname}", config_entry.entry_id, calendar_types, coordinator
        )
        entities.append(calendar_item_to_add)

    async_add_entities(entities)


class SLCVacationCalendarEntity(CoordinatorEntity, CalendarEntity):
    """Representation of a Skyline Communications Calendar element."""

    _attr_has_entity_name = False
    _entries: list[CalendarEntry] = []
    _calendar_types: list[CalendarEntryType] = []
    coordinator: CalendarCoordinator

    def __init__(
        self,
        name: str,
        unique_id: str,
        calendar_types: list[CalendarEntryType],
        coordinator: CalendarCoordinator,
    ) -> None:
        """Initialize SLCVacationCalendarEntity."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._calendar_types = calendar_types
        self._entries = self.get_filtered_entries_by_types()
        self._event = self.get_current_or_upcoming_event()

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return self._event

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        self._entries = self.get_filtered_entries_by_types()
        self._event = self.get_current_or_upcoming_event()
        self.async_write_ha_state()

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""

        event_list: list[CalendarEvent] = []

        for event in self._entries:
            if start_date <= event.event_date <= end_date:
                event = self.get_calendar_event_from_calender_entry(event)
                event_list.append(event)

        return event_list

    def get_filtered_entries_by_types(self) -> list[CalendarEntry]:
        """Return only the entries from the correct CalendarEntryType defined in _calendar_types."""
        return [
            x for x in self.coordinator.entries if (x.category in self._calendar_types)
        ]

    def get_current_or_upcoming_event(self) -> CalendarEvent | None:
        """Return the current ongoing event if it exists, otherwise the next upcoming event. Return None if no relevant events exist."""

        # Current time with system timezone
        now = datetime.now().astimezone()

        current_event = None
        future_events = []

        for e in self._entries:
            if e.event_date <= now < e.end_date:
                # Currently ongoing
                current_event = e
                break  # stop at first ongoing event
            elif e.event_date > now:
                # Future events
                future_events.append(e)

        if current_event:
            return self.get_calendar_event_from_calender_entry(current_event)

        if future_events:
            # Next upcoming event
            next_event = min(future_events, key=lambda e: e.event_date)
            return self.get_calendar_event_from_calender_entry(next_event)

        return None

    def get_calendar_event_from_calender_entry(
        self, calendarEntry: CalendarEntry
    ) -> CalendarEvent:
        """Converts a CalendarEntry to a CalendarEvent."""
        summary = f"{calendarEntry.category.name} - {calendarEntry.name}"
        if calendarEntry.category == CalendarEntryType.Public_Holiday:
            summary = f"Holiday - {calendarEntry.description}"
        if calendarEntry.category == CalendarEntryType.Weekend:
            summary = f"Weekend"
        return self.normalize_calendar_event(
            CalendarEvent(
                uid=calendarEntry.id,
                summary=summary,
                start=calendarEntry.event_date,
                end=calendarEntry.end_date,
                description=f"{calendarEntry.description} - {calendarEntry.name}",
            )
        )

    def is_all_day_or_multi_day_calendar_event(self, event: CalendarEvent) -> bool:
        """Detects single or multi day events that are 'all day long'."""
        start = event.start
        end = event.end

        # ----- CASE 1: Native HA all-day event (uses date objects) -----
        if (
            isinstance(start, date)
            and not isinstance(start, datetime)
            and isinstance(end, date)
            and not isinstance(end, datetime)
        ):
            return True

        # ----- CASE 2: datetime base => 00:00 → 23:59 or 00:00 → 00:00  -----
        if isinstance(start, datetime) and isinstance(end, datetime):
            # Normalize seconds
            start = start.replace(second=0)
            end = end.replace(second=0)

            midnight = time(0, 0, 0)
            almost_midnight = time(23, 59, 0)

            if (start.time() == midnight and end.time() == almost_midnight) or (
                start.time() == midnight
                and end.time() == midnight
                and start.date() != end.date()
            ):
                return True

        return False

    def normalize_calendar_event(self, event: CalendarEvent) -> CalendarEvent:
        """Return a new Home Assistant–normalized CalendarEvent."""
        if self.is_all_day_or_multi_day_calendar_event(event):
            # Convert start to date if datetime
            if isinstance(event.start, datetime):
                event.start = event.start.date()
            # Convert end to date if datetime
            if isinstance(event.end, datetime):
                event.end = event.end.date()

            # HA: end is *exclusive*, so always +1 day
            event.end = event.end + timedelta(days=1)
        return event

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
