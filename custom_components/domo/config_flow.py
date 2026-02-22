"""Config flow for ETI Domo integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import callback

from .const import DOMAIN, DEFAULT_HOST, DEFAULT_USERNAME, DEFAULT_PASSWORD
from .gateway import DomoGateway

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
    }
)


class DomoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ETI Domo."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is None:
            # Mostra il form con le istruzioni
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors=errors,
                description_placeholders={},
            )

        # Protezione duplicati
        await self.async_set_unique_id(user_input[CONF_HOST])
        self._abort_if_unique_id_configured()
        
        # Test connessione
        gateway = DomoGateway(
            self.hass,
            host=user_input[CONF_HOST],
            username=user_input[CONF_USERNAME],
            password=user_input[CONF_PASSWORD],
        )
        
        try:
            if await gateway.test_connection():
                return self.async_create_entry(
                    title=user_input[CONF_HOST],
                    data=user_input
                )
            else:
                errors["base"] = "cannot_connect"
        except Exception as err:
            _LOGGER.error("Login failed: %s", err)
            errors["base"] = "cannot_connect"
        finally:
            await gateway.stop()

        # Mostra di nuovo il form con l'errore
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return DomoOptionsFlow(config_entry)


class DomoOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for ETI Domo."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        super().__init__()
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        if user_input is not None:
            # Test connessione con nuove credenziali
            gateway = DomoGateway(
                self.hass,
                host=user_input[CONF_HOST],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            )
            
            try:
                if await gateway.test_connection():
                    # Aggiorna la entry esistente
                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        data=user_input
                    )
                    return self.async_create_entry(title="", data={})
                else:
                    errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.error("Login failed: %s", err)
                errors["base"] = "cannot_connect"
            finally:
                await gateway.stop()

        # Pre-popola con i valori esistenti
        current_host = self._config_entry.data.get(CONF_HOST, DEFAULT_HOST)
        current_username = self._config_entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)
        current_password = self._config_entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD)

        options_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current_host): str,
                vol.Required(CONF_USERNAME, default=current_username): str,
                vol.Required(CONF_PASSWORD, default=current_password): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
            description_placeholders={},
        )
