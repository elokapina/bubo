import logging

from nio import AsyncClient, RoomVisibility, EnableEncryptionBuilder

from storage import Storage

logger = logging.getLogger(__name__)


async def ensure_room_exists(room: tuple, client: AsyncClient):
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
        room_id = await client.room_resolve_alias(alias)
        if not room_id:
            # Create room
            response = await client.room_create(
                visibility=RoomVisibility.public if public else RoomVisibility.private,
                alias=alias,
                name=name,
                topic=title,
                initial_state=state,
                power_level_override=power_level_override,
            )
        # TODO save to storage

    # TODO fix room if needed

    # TODO Add rooms to communities


async def maintain_configured_rooms(client: AsyncClient, store: Storage):
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
        await ensure_room_exists(room, client)
        room = results.fetchone()
