"""Integration 101 Template integration using DataUpdateCoordinator."""

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .CalendarApi import CalendarEntry, CalendarException, CalendarHelper
from .const import (
    CONF_ELEMENT_ID,
    CONF_FULLNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    DOMAIN_METRICS_URL,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class CalendarAPIData:
    """Class to hold api data."""

    controller_name: str
    calender_entries: list[CalendarEntry]


class CalendarCoordinator(DataUpdateCoordinator):
    """My example coordinator."""

    data: CalendarAPIData

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""

        # Set variables from values entered in config flow setup
        self.host = DOMAIN_METRICS_URL
        self.api_key = config_entry.data[CONF_API_KEY]
        self.fullname = config_entry.data[CONF_FULLNAME]
        self.element_id = config_entry.data[CONF_ELEMENT_ID]

        # set variables from options.  You need a default here incase options have not been set
        # self.poll_interval = config_entry.options.get(
        #    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        # )
        self.poll_interval = DEFAULT_SCAN_INTERVAL

        # Initialise DataUpdateCoordinator
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            # Method to call on every update interval.
            update_method=self.async_update_data,
            # Polling interval. Will only be polled if there are subscribers.
            # Using config option here but you can just use a value.
            update_interval=timedelta(seconds=self.poll_interval),
        )

        # Initialise your api here
        self.api = CalendarHelper(self.api_key)

    async def async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            await self.api.authenticate_async(self.hass)
            calender_entries = await self.api.get_entries_async(
                self.hass, self.fullname, self.element_id
            )
        except CalendarException as err:
            _LOGGER.error(err)
            raise UpdateFailed(err) from err
        except Exception as err:
            # This will show entities as unavailable by raising UpdateFailed exception
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        # What is returned here is stored in self.data by the DataUpdateCoordinator
        return CalendarAPIData(self.fullname, calender_entries)

    def get_calendar_entries_by_fullname(
        self, fullname: str
    ) -> list[CalendarEntry] | None:
        """Return calendar entries by fullname."""
        # Called by the binary sensors and sensors to get their updated data from self.data
        try:
            return [
                entry for entry in self.data.calender_entries if entry.name == fullname
            ]
        except IndexError:
            return None
