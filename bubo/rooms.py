import logging
import time
from copy import deepcopy
from typing import Tuple, Optional, List, Dict

# noinspection PyPackageRequirements
from nio import AsyncClient, RoomVisibility, EnableEncryptionBuilder, RoomPutStateError

from bubo.chat_functions import invite_to_room
from bubo.config import Config
from bubo.storage import Storage
from bubo.utils import with_ratelimit

logger = logging.getLogger(__name__)


async def create_breakout_room(
    name: str, client: AsyncClient, created_by: str
) -> Dict:
    """
    Create a breakout room.
    """
    logger.info(f"Attempting to create breakout room '{name}'")
    response = await with_ratelimit(
        client,
        "room_create",
        name=name,
        visibility=RoomVisibility.private,
    )
    if getattr(response, "room_id", None):
        room_id = response.room_id
        logger.info(f"Breakout room '{name}' created at {room_id}")
    else:
        raise Exception(f"Could not create breakout room: {response.message}, {response.status_code}")
    await set_user_power(room_id, created_by, client, 100)
    await invite_to_room(client, room_id, created_by)
    return room_id


async def ensure_room_encrypted(room_id: str, client: AsyncClient):
    """
    Ensure room is encrypted.
    """
    state = await client.room_get_state_event(room_id, "m.room.encryption")
    if state.content.get('errcode') == 'M_NOT_FOUND':
        event_dict = EnableEncryptionBuilder().as_dict()
        response = await client.room_put_state(
            room_id=room_id,
            event_type=event_dict["type"],
            content=event_dict["content"],
        )
        if isinstance(response, RoomPutStateError):
            if response.status_code == "M_LIMIT_EXCEEDED":
                time.sleep(3)
                return ensure_room_encrypted(room_id, client)


async def ensure_room_power_levels(
        room_id: str, client: AsyncClient, config: Config, members: List,
):
    """
    Ensure room has correct power levels.
    """
    logger.debug(f"Ensuring power levels: {room_id}")
    state = await with_ratelimit(client, "room_get_state_event", room_id=room_id, event_type="m.room.power_levels")
    users = state.content["users"].copy()
    member_ids = {member.user_id for member in members}

    # check existing users
    for mxid, level in users.items():
        if mxid == config.user_id:
            continue

        # Promote users if they need more power
        if config.permissions_promote_users:
            if mxid in (config.admins + config.coordinators) and mxid in member_ids and level < 50:
                users[mxid] = 50
        # Demote users if they should have less power
        if config.permissions_demote_users:
            if mxid not in (config.admins + config.coordinators) and level > 0:
                users[mxid] = 0
        # Always demote users with too much power if not in the room
        if mxid not in member_ids:
            users[mxid] = 0

    # check new users
    if config.permissions_promote_users:
        for user in (config.admins + config.coordinators):
            if user in member_ids:
                users[user] = 50

    power_levels = config.rooms.get("power_levels") if config.rooms.get("enforce_power_in_old_rooms", True) else {}
    new_power = deepcopy(state.content)
    new_power.update(power_levels)
    new_power["users"] = users

    if state.content != new_power:
        logger.info(f"Updating room {room_id} power levels")
        response = await with_ratelimit(
            client,
            "room_put_state",
            room_id=room_id,
            event_type="m.room.power_levels",
            content=new_power,
        )
        logger.debug(f"Power levels update response: {response}")


async def ensure_room_exists(
        room: tuple, client: AsyncClient, store: Storage, config: Config,
) -> Tuple[str, Optional[str]]:
    """
    Maintains a room.
    """
    dbid, name, alias, room_id, title, icon, encrypted, public, room_type = room
    logger.debug(f"Ensuring room: {room}")
    room_created = False
    logger.info(f"Ensuring room {name} ({alias}) exists")
    state = []
    if encrypted:
        state.append(
            EnableEncryptionBuilder().as_dict(),
        )
    # Check if room exists
    if not room_id:
        logger.info(f"Room '{alias}' ID unknown")
        response = await client.room_resolve_alias(f"#{alias}:{config.server_name}")
        if getattr(response, "room_id", None):
            room_id = response.room_id
            logger.info(f"Room '{alias}' resolved to {room_id}")
        else:
            logger.info(f"Could not resolve room '{alias}', will try create")
            # Create room
            response = await client.room_create(
                visibility=RoomVisibility.public if public else RoomVisibility.private,
                alias=alias,
                name=name,
                topic=title,
                initial_state=state,
                power_level_override=config.rooms.get("power_levels"),
            )
            if getattr(response, "room_id", None):
                room_id = response.room_id
                logger.info(f"Room '{alias}' created at {room_id}")
                room_created = True
            else:
                if response.status_code == "M_LIMIT_EXCEEDED":
                    # Wait and try again
                    logger.info("Hit request limits, waiting 3 seconds...")
                    time.sleep(3)
                    return await ensure_room_exists(room, client, store, config)
                raise Exception(f"Could not create room: {response.message}, {response.status_code}")
        if dbid:
            # Store room ID
            store.cursor.execute("""
                update rooms set room_id = ? where id = ?
            """, (room_id, dbid))
            store.conn.commit()
            logger.info(f"Room '{alias}' room ID stored to database")
        else:
            store.cursor.execute("""
                insert into rooms (
                    name, alias, room_id, title, encrypted, public
                ) values (
                    ?, ?, ?, ?, ?, ?
                )
            """, (name, alias, room_id, title, encrypted, public))
            store.conn.commit()
            logger.info(f"Room '{alias}' creation stored to database")

    if encrypted:
        await ensure_room_encrypted(room_id, client)

        # TODO ensure room name + title
        # TODO ensure room alias

    # TODO Add rooms to communities

    room_members = await with_ratelimit(client, "joined_members", room_id)
    members = getattr(room_members, "members", [])

    await ensure_room_power_levels(room_id, client, config, members)

    if room_created:
        return "created", None
    return "exists", None


async def set_user_power(room_id: str, user_id: str, client: AsyncClient, power: int):
    """
    Set user power in a room.
    """
    logger.debug(f"Setting user power: {room_id}, user: {user_id}, level: {power}")
    state = await client.room_get_state_event(room_id, "m.room.power_levels")
    state.content["users"][user_id] = power
    response = await with_ratelimit(
        client,
        "room_put_state",
        room_id=room_id,
        event_type="m.room.power_levels",
        content=state.content,
    )
    logger.debug(f"Power levels update response: {response}")


async def maintain_configured_rooms(client: AsyncClient, store: Storage, config: Config):
    """
    Maintains the list of configured rooms.

    Creates if missing. Corrects if details are not correct.
    """
    logger.info("Starting maintaining of rooms")

    results = store.cursor.execute("""
        select * from rooms
    """)

    rooms = results.fetchall()
    for room in rooms:
        try:
            await ensure_room_exists(room, client, store, config)
        except Exception as e:
            logger.error(f"Error with room '{room[2]}': {e}")
