from dataclasses import dataclass  # noqa: D100
from datetime import datetime
from enum import Enum

import requests
import requests.packages

from homeassistant.core import HomeAssistant

from .const import DOMAIN_METRICS_URL


class CalendarEntryType(Enum):
    """Calendar Category Type."""

    Absent = 0
    WfH = 1
    RT_Rotation = 2
    Support_Rotation = 3
    Other = 4
    Public_Holiday = 5
    Weekend = 6
    Release = 7
    Seal = 8


@dataclass
class CalendarEntry:
    """A Calendar Entry."""

    id: str
    name: str
    category: CalendarEntryType
    event_date: datetime
    end_date: datetime
    description: str
    original_event_date: datetime
    originale_end_date: datetime


class CalendarHelper:
    """Wrapper around the calendar api."""

    def __init__(self, api_key: str = "", element_id: str = "") -> None:
        """Initialize."""

        self.api_key = api_key

    def authenticate(self) -> None:
        """Validate if the given api key is valid."""

        url = DOMAIN_METRICS_URL + "/api/custom/calendar/ping"
        headers = {"Authorization": "Bearer " + self.api_key}
        response = requests.get(url=url, verify=True, headers=headers)
        data = response.text
        if data != "pong":
            raise CalendarException("Could not authenticate")

    async def authenticate_async(self, hass: HomeAssistant) -> None:
        """Validate if the given api key is valid async."""

        return await hass.async_add_executor_job(self.authenticate)

    def get_entries(self, fullname: str, element_id: str) -> list[CalendarEntry]:
        """Get the entries for a given user."""

        url = (
            DOMAIN_METRICS_URL
            + f"/api/custom/calendar?elementId={element_id}&fullname={fullname}"
        )
        headers = {"Authorization": "Bearer " + self.api_key}
        response = requests.get(url=url, verify=True, headers=headers)

        entries: list[CalendarEntry] = []
        jsonResponse = response.json()
        if response.status_code >= 400:
            raise CalendarException(jsonResponse["errors"][0]["detail"])

        for temp in jsonResponse:
            entry = CalendarEntry(
                id=temp["ID"],
                name=temp["Name"],
                category=CalendarEntryType(temp["Category"]),
                event_date=datetime.strptime(temp["EventDate"], "%Y-%m-%dT%H:%M:%S"),
                end_date=datetime.strptime(temp["EndDate"], "%Y-%m-%dT%H:%M:%S"),
                description=temp["Description"],
                original_event_date=datetime.strptime(
                    temp["OriginalEventDate"], "%Y-%m-%dT%H:%M:%S"
                ),
                originale_end_date=datetime.strptime(
                    temp["OriginalEndDate"], "%Y-%m-%dT%H:%M:%S"
                ),
            )
            entries.append(entry)

        return entries

    async def get_entries_async(
        self, hass: HomeAssistant, fullname: str, element_id: str
    ):
        """Get the entries for a given user async."""

        return await hass.async_add_executor_job(self.get_entries, fullname, element_id)


class CalendarException(Exception):
    """Error to indicate there is exception with the Calendar API."""
