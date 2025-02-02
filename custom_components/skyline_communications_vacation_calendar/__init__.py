"""The Skyline Communications Vacation Calendar integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .coordinator import CalendarCoordinator

# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR]


@dataclass
class RuntimeData:
    """Class to hold your data."""

    coordinator: DataUpdateCoordinator
    cancel_update_listener: Callable


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Skyline Communications Vacation Calendar from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    # Initialise the coordinator that manages data updates from your api.
    # This is defined in coordinator.py
    coordinator = CalendarCoordinator(hass, config_entry)

    # Perform an initial data load from api.
    # async_config_entry_first_refresh() is special in that it does not log errors if it fails
    await coordinator.async_config_entry_first_refresh()

    # Initialise a listener for config flow options changes.
    # See config_flow for defining an options setting that shows up as configure on the integration.
    cancel_update_listener = config_entry.async_on_unload(
        config_entry.add_update_listener(_async_update_listener)
    )

    # Add the coordinator and update listener to hass data to make
    # accessible throughout your integration
    # Note: this will change on HA2024.6 to save on the config entry.
    hass.data[DOMAIN][config_entry.entry_id] = RuntimeData(
        coordinator, cancel_update_listener
    )

    # Setup platforms (based on the list of entity types in PLATFORMS defined above)
    # This calls the async_setup method in each of your entity type files.
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    # Return true to denote a successful setup.
    return True


async def _async_update_listener(hass: HomeAssistant, config_entry):
    """Handle config options update."""
    # Reload the integration when the options change.
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Delete device if selected from UI."""
    # Adding this function shows the delete device option in the UI.
    # Remove this function if you do not want that option.
    # You may need to do some checks here before allowing devices to be removed.
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload services
    for service in hass.services.async_services_for_domain(DOMAIN):
        hass.services.async_remove(DOMAIN, service)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    # Remove the config entry from the hass data object.
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    # Return that unloading was successful.
    return unload_ok
