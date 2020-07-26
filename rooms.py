import logging

from storage import Storage

logger = logging.getLogger(__name__)


async def ensure_room_exists(room: tuple):
    """
    Maintains a room.
    """
    dbid, name, alias, room_id, title, icon, encrypted, public, power_to_write = room
    logger.info(f"Ensuring room {name} ({alias}) exists")
    # TODO: do actual ensuring


async def maintain_configured_rooms(store: Storage):
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
        await ensure_room_exists(room)
        room = results.fetchone()
