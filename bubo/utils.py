import logging
import time
from typing import Set

# noinspection PyPackageRequirements
from nio import AsyncClient, JoinedMembersResponse, RoomResolveAliasError, ProtocolError

from bubo.config import Config

logger = logging.getLogger(__name__)


async def ensure_room_id(client: AsyncClient, room_id_or_alias: str) -> str:
    if room_id_or_alias.startswith("#"):
        response = await client.room_resolve_alias(room_id_or_alias)
        if isinstance(response, RoomResolveAliasError):
            raise ProtocolError(f"Could not resolve {room_id_or_alias} room ID")
        return response.room_id
    return room_id_or_alias


def get_request_headers(config):
    return {
        "Authorization": f"Bearer {config.user_token}",
    }


async def get_users_for_access(client: AsyncClient, config: Config, access_type: str) -> Set:
    if access_type == "admins":
        existing_list = list(set(config.admins[:]))
    elif access_type == "coordinators":
        existing_list = list(set(config.admins[:] + config.coordinators[:]))
    elif access_type == "pindora_users":
        existing_list = list(set(config.pindora_users[:]))
    else:
        logger.error(f"Invalid access type: {access_type}")
        return set()
    users = existing_list[:]
    for room_id in existing_list:
        if not room_id.startswith("!"):
            continue
        response = await with_ratelimit(client=client, method="joined_members", room_id=room_id)
        if isinstance(response, JoinedMembersResponse):
            logger.debug(f"Found {len(response.members)} users for {access_type} access type in room {room_id}")
            users.extend([member.user_id for member in response.members])
        else:
            logger.warning(f"Failed to get list of users for access from room {room_id}: {response.message}")
    return set(users)


# TODO remove usage of this wrapper for any matrix-nio calls
# Reading that code it seems it already handles rate limits 😅
async def with_ratelimit(client: AsyncClient, method: str, *args, **kwargs):
    func = getattr(client, method)
    response = await func(*args, **kwargs)
    if getattr(response, "status_code", None) == "M_LIMIT_EXCEEDED":
        time.sleep(3)
        return with_ratelimit(client, method, *args, **kwargs)
    return response
