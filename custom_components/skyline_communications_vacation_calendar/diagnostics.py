"""Diagnostics support for Skyline Communications Vacation Calendar."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import CalendarCoordinator

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: CalendarCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    return {
        "config_entry_data": async_redact_data(dict(config_entry.data), TO_REDACT),
        "observation_data": coordinator.entries,
    }
