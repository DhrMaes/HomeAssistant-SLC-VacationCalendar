from dataclasses import dataclass
import datetime
import requests
import requests.packages
from enum import Enum
from typing import List, Dict

from const import DOMAIN_METRICS_URL

class CalendarEntryType(Enum):
    """Calendar Category Type"""
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
    """A Calendar Entry"""
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

    def __init__(self, api_key: str = '', element_id: str = '') -> None:
        """Initialize."""

        self.api_key = api_key
        self.element_id = element_id

    def authenticate(self) -> None:
        """Validate if the given api key is valid."""

        url = DOMAIN_METRICS_URL + "/api/custom/calendar/ping"
        headers = { "Authorization": "Bearer " + self.api_key }
        response = requests.get(
            url = url,
            verify = True,
            headers = headers
        )
        data = response.text
        if data != "pong":
            raise CalendarException("Could not authenticate")

    def getEntries(self, fullname: str = '') -> list[CalendarEntry]:
        """Get the entries for a given user."""

        url = DOMAIN_METRICS_URL + f"/api/custom/calendar?elementId={self.element_id}&fullname={fullname}"
        headers = { "Authorization": "Bearer " + self.api_key }
        response = requests.get(
            url = url,
            verify = True,
            headers = headers
        )

        entries: list[CalendarEntry] = []
        jsonResponse = response.json()
        for temp in jsonResponse:
            entry = CalendarEntry(
                id=temp["ID"],
                name=temp["Name"],
                category=temp["Category"],
                event_date=temp["EventDate"],
                end_date=temp["EndDate"],
                description=temp["Description"],
                original_event_date=temp["OriginalEventDate"],
                originale_end_date=temp["OriginalEndDate"]
            )
            entries.append(entry)

        if(response.status_code >= 200 and response.status_code <= 299):
            return entries
        raise Exception(jsonResponse["errors"][0]["detail"])
    
class CalendarException(Exception):
    """Error to indicate there is exception with the Calendar API."""