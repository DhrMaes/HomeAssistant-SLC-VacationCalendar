"""Config flow for the Skyline Communications Vacation Calendar integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_ELEMENT_ID,
    CONF_FULLNAME,
    CONF_OPTION_CALENDAR_ENTITY_FOREACH_TYPE,
    CONF_OPTION_CALENDAR_TYPES,
    DOMAIN,
    SERVICE_NAME,
)
from .skyline.calendar_api import (
    CalendarEntryType,
    CalendarException,
    CalendarHelper,
    get_calendar_type_display_value,
)

_LOGGER = logging.getLogger(__name__)

possible_calendar_types = [
    SelectOptionDict(
        value=str(CalendarEntryType.Absent.value),
        label=get_calendar_type_display_value(CalendarEntryType.Absent),
    ),
    SelectOptionDict(
        value=str(CalendarEntryType.Public_Holiday.value),
        label=get_calendar_type_display_value(CalendarEntryType.Public_Holiday),
    ),
    SelectOptionDict(
        value=str(CalendarEntryType.WfH.value),
        label=get_calendar_type_display_value(CalendarEntryType.WfH),
    ),
    SelectOptionDict(
        value=str(CalendarEntryType.Weekend.value),
        label=get_calendar_type_display_value(CalendarEntryType.Weekend),
    ),
]

default_calendar_types = [
    str(CalendarEntryType.Absent.value),
    str(CalendarEntryType.Public_Holiday.value),
    str(CalendarEntryType.WfH.value),
]

default_calendar_entity_foreach_type = True


STEP_USER_AUTHENTICATION_SCHEME = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
    }
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_FULLNAME): str,
        vol.Required(CONF_ELEMENT_ID): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    api = CalendarHelper(data[CONF_API_KEY])
    await api.authenticate_async(hass)
    # Return info that you want to store in the config entry.
    return {"title": SERVICE_NAME}


class SLCVacationCalendarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Skyline Communications Vacation Calendar."""

    VERSION = 1
    MINOR_VERSION = 1

    _input_data: dict[str, Any]
    _title: str

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                api = CalendarHelper(user_input[CONF_API_KEY])
                await api.authenticate_async(self.hass)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if "base" not in errors:
                # Validation was successful, so proceed to the next step.

                # ----------------------------------------------------------------------------
                # You need to save the input data to a class variable as you go through each step
                # to ensure it is accessible across all steps.
                # ----------------------------------------------------------------------------
                self._input_data = user_input

                # Call the next step
                return await self.async_step_settings()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_AUTHENTICATION_SCHEME,
            errors=errors,
            last_step=False,
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the second step.

        Our second config flow step.
        Works just the same way as the first step.
        Except as it is our last step, we create the config entry after any validation.
        """

        errors: dict[str, str] = {}

        if user_input is not None:
            # The form has been filled in and submitted, so process the data provided.
            try:
                api = CalendarHelper(self._input_data[CONF_API_KEY])
                await api.get_entries_async(
                    self.hass, user_input[CONF_FULLNAME], user_input[CONF_ELEMENT_ID]
                )
                # info = await validate_input(self.hass, user_input)
            except CalendarException as ce:
                _LOGGER.exception()
                errors["base"] = f"{ce}"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if "base" not in errors:
                # ----------------------------------------------------------------------------
                # Validation was successful, so create the config entry.
                # ----------------------------------------------------------------------------
                self._title = f"{SERVICE_NAME} - {user_input[CONF_FULLNAME]}"
                await self.async_set_unique_id(self._title)
                self._abort_if_unique_id_configured()

                self._input_data.update(user_input)
                return self.async_create_entry(title=self._title, data=self._input_data)

        # ----------------------------------------------------------------------------
        # Show settings form.  The step id always needs to match the bit after async_step_ in your method.
        # Set last_step to True here if it is last step.
        # ----------------------------------------------------------------------------
        return self.async_show_form(
            step_id="settings",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            last_step=True,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add reconfigure step to allow to reconfigure a config entry."""
        # This methid displays a reconfigure option in the integration and is
        # different to options.
        # It can be used to reconfigure any of the data submitted when first installed.
        # This is optional and can be removed if you do not want to allow reconfiguration.
        errors: dict[str, str] = {}
        config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    config_entry,
                    unique_id=config_entry.unique_id,
                    data={**config_entry.data, **user_input},
                    reason="reconfigure_successful",
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_KEY, default=config_entry.data[CONF_API_KEY]
                    ): str,
                    vol.Required(
                        CONF_FULLNAME, default=config_entry.data[CONF_FULLNAME]
                    ): str,
                    vol.Required(
                        CONF_ELEMENT_ID, default=config_entry.data[CONF_ELEMENT_ID]
                    ): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlow):
    """Handle a option flow for Skyline Communications Vacation Calendar."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_OPTION_CALENDAR_TYPES,
                    default=self.config_entry.options.get(
                        CONF_OPTION_CALENDAR_TYPES, default_calendar_types
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=possible_calendar_types,
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_OPTION_CALENDAR_ENTITY_FOREACH_TYPE,
                    default=self.config_entry.options.get(
                        CONF_OPTION_CALENDAR_ENTITY_FOREACH_TYPE,
                        default_calendar_entity_foreach_type,
                    ),
                ): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
