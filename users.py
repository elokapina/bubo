import json
from typing import List, Dict, Optional

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


def create_user(config: Config, username: str, email: str) -> Optional[str]:
    if not config.users.get('provider'):
        return
    keycloak_admin = get_admin_client(config)
    return keycloak_admin.create_user({
        "email": email,
        "emailVerified": True,
        "enabled": True,
        "username": username,
    })


def send_password_reset(config: Config, user_id: str) -> Dict:
    if not config.users.get('provider'):
        return {}
    keycloak_admin = get_admin_client(config)
    keycloak_admin.send_update_account(
        user_id=user_id,
        payload=json.dumps(['UPDATE_PASSWORD']),
    )


def get_user_by_attr(config: Config, attr: str, value: str) -> Optional[Dict]:
    if not config.users.get('provider'):
        return
    keycloak_admin = get_admin_client(config)
    users = keycloak_admin.get_users({
        attr: value,
    })
    if len(users) == 1:
        return users[0]
    elif len(users) > 1:
        raise Exception(f"More than one user found with the same {attr} = {value}")


def list_users(config: Config) -> List[Dict]:
    if not config.users.get('provider'):
        return []
    keycloak_admin = get_admin_client(config)
    users = keycloak_admin.get_users({})
    return users
