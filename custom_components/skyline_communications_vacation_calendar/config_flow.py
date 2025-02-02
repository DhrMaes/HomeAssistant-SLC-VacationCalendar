"""Config flow for the Skyline Communications Vacation Calendar integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .CalendarApi import CalendarException, CalendarHelper
from .const import CONF_ELEMENT_ID, CONF_FULLNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

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
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data[CONF_USERNAME], data[CONF_PASSWORD]
    # )

    api = CalendarHelper(data[CONF_API_KEY])
    await api.authenticate_async(hass)

    # if not await api.authenticate():
    #     raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": "SLC Vacation Calendar"}


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Skyline Communications Vacation Calendar."""

    VERSION = 1
    MINOR_VERSION = 1

    _input_data: dict[str, Any]
    _title: str

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                api = CalendarHelper(user_input[CONF_API_KEY])
                await api.authenticate_async(self.hass)
                # info = await validate_input(self.hass, user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if "base" not in errors:
                # Validation was successful, so create a unique id for this instance of your integration
                # and create the config entry.
                # await self.async_set_unique_id("SLC Vacation Calendar")
                # self._abort_if_unique_id_configured()
                # return self.async_create_entry(
                #     title="SLC Vacation Calendar", data=user_input
                # )

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
                self._title = f"SLC Vacation Calendar - {user_input[CONF_FULLNAME]}"
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


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
