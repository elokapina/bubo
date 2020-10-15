import logging
import time

from typing import Tuple, Optional

# noinspection PyPackageRequirements
from nio import AsyncClient, RoomVisibility, EnableEncryptionBuilder, RoomPutStateError

from config import Config
from storage import Storage

logger = logging.getLogger(__name__)


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


async def ensure_room_power_levels(room_id: str, client: AsyncClient, config: Config, power_to_write: int):
    """
    Ensure room has correct power levels.
    """
    state = await client.room_get_state_event(room_id, "m.room.power_levels")
    users = state.content["users"].copy()

    # check existing users
    for mxid, level in users.items():
        if mxid == config.user_id:
            continue

        if config.permissions_promote_users:
            if mxid in (config.admins + config.coordinators) and level < 50:
                users[mxid] = 50
        if config.permissions_demote_users:
            if mxid not in (config.admins + config.coordinators) and level > 0:
                users[mxid] = 0

    # check new users
    if config.permissions_promote_users:
        for user in (config.admins + config.coordinators):
            users[user] = 50

    if state.content["users"] != users or state.content.get("events_default") != power_to_write:
        state.content["events_default"] = power_to_write
        state.content["users"] = users
        response = await client.room_put_state(
            room_id=room_id,
            event_type="m.room.power_levels",
            content=state.content,
        )
        if isinstance(response, RoomPutStateError):
            if response.status_code == "M_LIMIT_EXCEEDED":
                time.sleep(3)
                return ensure_room_power_levels(room_id, client, config, power_to_write)


async def ensure_room_exists(
        room: tuple, client: AsyncClient, store: Storage, config: Config,
) -> Tuple[str, Optional[str]]:
    """
    Maintains a room.
    """
    dbid, name, alias, room_id, title, icon, encrypted, public, power_to_write, room_type = room
    room_created = False
    logger.info(f"Ensuring room {name} ({alias}) exists")
    state = []
    if encrypted:
        state.append(
            EnableEncryptionBuilder().as_dict(),
        )
    power_level_override = {
        "events_default": power_to_write,
    }
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
                power_level_override=power_level_override,
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

    await ensure_room_power_levels(room_id, client, config, power_to_write)

    if room_created:
        return "created", None
    return "exists", None


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
