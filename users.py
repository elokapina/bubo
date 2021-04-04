from typing import List, Dict

# noinspection PyPackageRequirements
from keycloak import KeycloakAdmin

from config import Config


def get_admin_client(config: Config) -> KeycloakAdmin:
    params = {
        "server_url": config.users["provider"]["url"],
        "realm_name": config.users["provider"]["realm_name"],
        "client_secret_key": config.users["provider"]["client_secret_key"],
        "verify": True,
    }
    return KeycloakAdmin(**params)


async def list_users(config: Config) -> List[Dict]:
    if not config.users.get('provider'):
        return []
    keycloak_admin = get_admin_client(config)
    users = keycloak_admin.get_users({})
    return users
