# noinspection PyPackageRequirements
from nio import JoinError

from bubo.bot_commands import Command
from bubo.chat_functions import send_text_to_room, invite_to_room
from bubo.message_responses import Message

import logging
logger = logging.getLogger(__name__)


class Callbacks(object):

    def __init__(self, client, store, config):
        """
        Args:
            client (nio.AsyncClient): nio client used to interact with matrix

            store (Storage): Bot storage

            config (Config): Bot configuration parameters
        """
        self.client = client
        self.store = store
        self.config = config
        self.command_prefix = config.command_prefix

    async def message(self, room, event):
        """Callback for when a message event is received

        Args:
            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMessageText): The event defining the message

        """
        # Extract the message text
        msg = event.body

        # Ignore messages from ourselves
        if event.sender == self.client.user:
            return

        # If this looks like an edit, strip the edit prefix
        if msg.startswith(" * "):
            msg = msg[3:]

        logger.debug(
            f"Bot message received for room {room.display_name} | "
            f"{room.user_name(event.sender)}: {msg}"
        )

        # Process as message if in a public room without command prefix
        has_command_prefix = msg.startswith(self.command_prefix)
        if not has_command_prefix and not room.is_group:
            # General message listener
            message = Message(self.client, self.store, self.config, msg, room, event)
            await message.process()
            return

        # Otherwise if this is in a 1-1 with the bot or features a command prefix,
        # treat it as a command
        if has_command_prefix:
            # Remove the command prefix
            msg = msg[len(self.command_prefix):]

        command = Command(self.client, self.store, self.config, msg, room, event)
        await command.process()

    async def reaction(self, room, event):
        """Callback for when a reaction is received."""
        logger.debug(f"Got unknown event to {room.room_id} from {event.sender}.")
        if event.type != "m.reaction":
            return
        relates_to = event.source.get("content", {}).get("m.relates_to")
        logger.debug(f"Relates to: {relates_to}")
        if not relates_to:
            return
        event_id = relates_to.get("event_id")
        rel_type = relates_to.get("rel_type")
        if not event_id or rel_type != "m.annotation":
            return
        # TODO split to "reactions.py" or similar
        # Breakout creation reaction?
        room_id = self.store.get_breakout_room_id(event_id)
        logger.debug(f"Breakout room query found room_id: {room_id}")
        if room_id:
            logger.info(f"Found breakout room for reaction in {room.room_id} by {event.sender} - "
                        f"inviting to {room_id}")
            # Do an invite
            await invite_to_room(
                self.client, room_id, event.sender,
            )

    async def invite(self, room, event):
        """Callback for when an invite is received. Join the room specified in the invite"""
        logger.debug(f"Got invite to {room.room_id} from {event.sender}.")

        # Attempt to join 3 times before giving up
        for attempt in range(3):
            result = await self.client.join(room.room_id)
            if type(result) == JoinError:
                logger.error(
                    f"Error joining room {room.room_id} (attempt %d): %s",
                    attempt, result.message,
                )
            else:
                break
        else:
            logger.error("Unable to join room: %s", room.room_id)

        # Successfully joined room
        logger.info(f"Joined {room.room_id}")

    async def decryption_failure(self, room, event):
        """Callback for when an event fails to decrypt. Inform the user"""
        logger.error(
            f"Failed to decrypt event '{event.event_id}' in room '{room.room_id}'!"
            f"\n\n"
            f"Tip: try using a different device ID in your config file and restart."
            f"\n\n"
            f"If all else fails, delete your store directory and let the bot recreate "
            f"it (your reminders will NOT be deleted, but the bot may respond to existing "
            f"commands a second time)."
        )
        if self.config.callbacks.get("unable_to_decrypt_responses", True):
            user_msg = (
                "Unable to decrypt this message. "
                "Check whether you've chosen to only encrypt to trusted devices."
            )

            await send_text_to_room(
                self.client, room.room_id, user_msg, reply_to_event_id=event.event_id,
            )
