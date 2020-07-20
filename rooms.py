import logging

from config import Config

logger = logging.getLogger(__name__)


async def maintain_configured_rooms(config: Config):
    """
    Maintains the list of configured rooms.

    Creates if missing. Corrects if details are not correct.
    """
    logger.info("Starting maintaining of rooms")

    for alias, data in config.rooms.items():
        print(alias, data)
