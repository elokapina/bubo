import time

import requests

from bubo.config import Config

API_PREFIX_V1 = "/_synapse/admin/v1"
API_PREFIX_V2 = "/_synapse/admin/v2"


def get_headers(config):
    return {
        "Authorization": f"Bearer {config.user_token}",
    }


def join_user(config: Config, user_id: str, room_id_or_alias: str) -> int:
    headers = get_headers(config)

    response = requests.post(
        f"{config.homeserver_url}{API_PREFIX_V1}/join/{room_id_or_alias}",
        json={
            "user_id": user_id,
        },
        headers=headers,
    )
    if response.status_code == 429:
        time.sleep(3)
        return join_user(config, user_id, room_id_or_alias)
    response.raise_for_status()
    return response.status_code
