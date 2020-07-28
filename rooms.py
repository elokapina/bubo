import logging

from nio import AsyncClient, RoomVisibility, EnableEncryptionBuilder

from config import Config
from storage import Storage

logger = logging.getLogger(__name__)


async def ensure_room_exists(room: tuple, client: AsyncClient, store: Storage, config: Config):
    """
    Maintains a room.
    """
    dbid, name, alias, room_id, title, icon, encrypted, public, power_to_write = room
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
            else:
                raise Exception(f"Could not create room: {response.message}, {response.status_code}")
        # Store room ID
        store.cursor.execute("""
            update rooms set room_id = ? where id = ?
        """, (room_id, dbid))
        store.conn.commit()
        logger.info(f"Room '{alias}' room ID stored to database")

    # TODO fix room if needed

    # TODO Add rooms to communities


async def maintain_configured_rooms(client: AsyncClient, store: Storage, config: Config):
    """
    Maintains the list of configured rooms.

    Creates if missing. Corrects if details are not correct.
    """
    logger.info("Starting maintaining of rooms")

    results = store.cursor.execute("""
        select * from rooms
    """)

    room = results.fetchone()
    while room:
        try:
            await ensure_room_exists(room, client, store, config)
        except Exception as e:
            logger.error(f"Error with room '{room[2]}': {e}")
        room = results.fetchone()
