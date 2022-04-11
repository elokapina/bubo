import asyncio
import logging
import time
from typing import List, Optional, Dict

import aiohttp

from bubo.config import Config
from bubo.utils import get_request_headers

logger = logging.getLogger(__name__)

API_PREFIX_V1 = "/_synapse/admin/v1"
API_PREFIX_V2 = "/_synapse/admin/v2"


async def get_temporary_user_token(
    config: Config, session: aiohttp.ClientSession, headers: Dict, user: str,
) -> Optional[str]:
    async with session.post(
        f"{config.homeserver_url}{API_PREFIX_V1}/users/{user}/login",
        json={
            "valid_until_ms": (int(time.time()) + 60*15) * 1000,  # 15 minutes
        },
        headers=headers,
    ) as response:
        if response.status == 429:
            await asyncio.sleep(1)
            return await get_temporary_user_token(config, session, headers, user)
        try:
            response.raise_for_status()
            data = await response.json()
            return data["access_token"]
        except Exception as ex:
            logger.warning("Failed to get temporary access token for user %s: %s", user, ex)
            return


async def get_temporary_user_tokens(config: Config, users: List[str]) -> Dict:
    headers = get_request_headers(config)
    tokens = {}
    async with aiohttp.ClientSession() as session:
        for user in users:
            token = await get_temporary_user_token(config, session, headers, user)
            if token:
                logger.debug("Got temporary token for user %s", user)
                tokens[user] = token
            else:
                logger.debug("Failed to get temporary token for user %s", user)
    return tokens


async def join_user(
    config: Config, headers: Dict, room_id_or_alias: str, session: aiohttp.ClientSession, user: str,
) -> bool:
    async with session.post(
        f"{config.homeserver_url}{API_PREFIX_V1}/join/{room_id_or_alias}",
        json={
            "user_id": user,
        },
        headers=headers,
    ) as response:
        if response.status == 429:
            await asyncio.sleep(1)
            return await join_user(config, headers, room_id_or_alias, session, user)
        try:
            response.raise_for_status()
            return True
        except Exception as ex:
            logger.warning("Failed to join user %s: %s", user, ex)
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


async def make_room_admin(config: Config, room_id: str, user_id: str) -> bool:
    headers = get_request_headers(config)
    async with aiohttp.ClientSession() as session:
        async with session.post(
                f"{config.homeserver_url}{API_PREFIX_V1}/rooms/{room_id}/make_room_admin",
                json={
                    "user_id": user_id,
                },
                headers=headers,
        ) as response:
            if response.status == 429:
                await asyncio.sleep(1)
                return await make_room_admin(config, room_id, user_id)
            try:
                response.raise_for_status()
                return True
            except Exception as ex:
                logger.warning("Failed to make room admin in %s for %s: %s", room_id, user_id, ex)
                return False
