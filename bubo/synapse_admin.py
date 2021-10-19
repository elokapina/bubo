import asyncio
from typing import List

import aiohttp

from bubo.config import Config
from bubo.utils import get_request_headers

API_PREFIX_V1 = "/_synapse/admin/v1"
API_PREFIX_V2 = "/_synapse/admin/v2"


async def join_user(config, headers, room_id_or_alias, session, user):
    async with session.post(
        f"{config.homeserver_url}{API_PREFIX_V1}/join/{room_id_or_alias}",
        json={
            "user_id": user,
        },
        headers=headers,
    ) as response:
        if response.status == 429:
            await asyncio.sleep(3)
            return await join_user(config, headers, room_id_or_alias, session, user)
        try:
            response.raise_for_status()
            return True
        except Exception:
            return False


async def join_users(config: Config, users: List[str], room_id_or_alias: str) -> int:
    headers = get_request_headers(config)

    total_joined = 0
    async with aiohttp.ClientSession() as session:
        for user in users:
            result = await join_user(config, headers, room_id_or_alias, session, user)
            if result:
                total_joined += 1
        return total_joined
