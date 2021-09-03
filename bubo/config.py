import logging
import re
import os
import yaml
import sys
from typing import List, Any

from aiolog import matrix
# noinspection PyPackageRequirements
from nio.schemas import check_user_id

from bubo.errors import ConfigError

logger = logging.getLogger()
logging.getLogger("peewee").setLevel(
    logging.INFO
)  # Prevent debug messages from peewee lib


class Config(object):
    def __init__(self, filepath):
        """
        Args:
            filepath (str): Path to config file
        """
        if not os.path.isfile(filepath):
            raise ConfigError(f"Config file '{filepath}' does not exist")

        # Load in the config file at the given filepath
        with open(filepath) as file_stream:
            self.config = yaml.safe_load(file_stream.read())

        # Logging setup
        formatter = logging.Formatter('%(asctime)s | %(name)s [%(levelname)s] %(message)s')

        log_level = self._get_cfg(["logging", "level"], default="INFO")
        logger.setLevel(log_level)

        file_logging_enabled = self._get_cfg(["logging", "file_logging", "enabled"], default=False)
        file_logging_filepath = self._get_cfg(["logging", "file_logging", "filepath"], default="bot.log")
        if file_logging_enabled:
            handler = logging.FileHandler(file_logging_filepath)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        console_logging_enabled = self._get_cfg(["logging", "console_logging", "enabled"], default=True)
        if console_logging_enabled:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        # Storage setup
        self.database_filepath = self._get_cfg(["storage", "database_filepath"], required=True)
        self.store_filepath = self._get_cfg(["storage", "store_filepath"], required=True)

        # Create the store folder if it doesn't exist
        if not os.path.isdir(self.store_filepath):
            if not os.path.exists(self.store_filepath):
                os.mkdir(self.store_filepath)
            else:
                raise ConfigError(f"storage.store_filepath '{self.store_filepath}' is not a directory")

        # Matrix bot account setup
        self.user_id = self._get_cfg(["matrix", "user_id"], required=True)
        if not re.match("@.*:.*", self.user_id):
            raise ConfigError("matrix.user_id must be in the form @name:domain")

        self.user_token = self._get_cfg(["matrix", "user_token"], required=False, default="")
        self.user_password = self._get_cfg(["matrix", "user_password"], required=False, default="")
        if not self.user_token and not self.user_password:
            raise ConfigError("Must supply either user token or password")

        self.device_id = self._get_cfg(["matrix", "device_id"], required=True)
        self.device_name = self._get_cfg(["matrix", "device_name"], default="nio-template")
        self.homeserver_url = self._get_cfg(["matrix", "homeserver_url"], required=True)
        self.server_name = self._get_cfg(["matrix", "server_name"], required=True)

        self.command_prefix = self._get_cfg(["command_prefix"], default="!c") + " "

        matrix_logging_enabled = self._get_cfg(["logging", "matrix_logging", "enabled"], default=False)
        if matrix_logging_enabled:
            if not self.user_token:
                logger.warning("Not setting up Matrix logging - requires user access token to be set")
            else:
                matrix_logging_room = self._get_cfg(["logging", "matrix_logging", "room"], required=True)
                handler = matrix.Handler(
                    homeserver_url=self.homeserver_url,
                    access_token=self.user_token,
                    room_id=matrix_logging_room,
                )
                handler.setFormatter(formatter)
                logger.addHandler(handler)

        # Permissions
        self.admins = self._get_cfg(["permissions", "admins"], default=[])
        try:
            for admin in self.admins:
                check_user_id(admin)
        except ValueError as e:
            raise ConfigError(str(e))
        self.coordinators = self._get_cfg(["permissions", "coordinators"], default=[])
        try:
            for coordinator in self.coordinators:
                check_user_id(coordinator)
        except ValueError as e:
            raise ConfigError(str(e))
        self.permissions_demote_users = self._get_cfg(["permissions", "demote_users"], default=False, required=False)
        self.permissions_promote_users = self._get_cfg(["permissions", "promote_users"], default=True, required=False)

        # Rooms
        self.rooms = self._get_cfg(["rooms"], default={}, required=False)

        # Callbacks
        self.callbacks = self._get_cfg(["callbacks"], default={}, required=False)

        # Keycloak
        self.keycloak = self._get_cfg(["users", "keycloak"], default={}, required=False)
        self.keycloak_signup = self._get_cfg(["users", "keycloak", "keycloak_signup"], default={}, required=False)

        # Email
        self.email = self._get_cfg(["email"], default={}, required=False)
        if self.email and self.email.get("starttls") and self.email.get("ssl"):
            raise ConfigError("Cannot enable both starttls and ssl for email")

    def _get_cfg(
            self,
            path: List[str],
            default: Any = None,
            required: bool = True,
    ) -> Any:
        """Get a config option from a path and option name, specifying whether it is
        required.

        Raises:
            ConfigError: If required is specified and the object is not found
                (and there is no default value provided), this error will be raised
        """
        # Sift through the the config until we reach our option
        config = self.config
        for name in path:
            config = config.get(name)

            # If at any point we don't get our expected option...
            if config is None:
                # Raise an error if it was required
                if required or default is False or default is None:
                    raise ConfigError(f"Config option {'.'.join(path)} is required")

                # or return the default value
                return default

        # We found the option. Return it
        return config
