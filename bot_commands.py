from nio import RoomInviteError
from nio.schemas import check_user_id

from chat_functions import send_text_to_room, invite_to_room

TEXT_PERMISSION_DENIED = "I'm afraid I cannot let you do that."


class Command(object):
    def __init__(self, client, store, config, command, room, event):
        """A command made by a user

        Args:
            client (nio.AsyncClient): The client to communicate to matrix with

            store (Storage): Bot storage

            config (Config): Bot configuration parameters

            command (str): The command and arguments

            room (nio.rooms.MatrixRoom): The room the command was sent in

            event (nio.events.room_events.RoomMessageText): The event describing the command
        """
        self.client = client
        self.store = store
        self.config = config
        self.command = command
        self.room = room
        self.event = event
        self.args = self.command.split()[1:]

    async def _ensure_admin(self) -> bool:
        if self.event.sender not in self.config.admins:
            await send_text_to_room(
                self.client,
                self.room.room_id,
                TEXT_PERMISSION_DENIED,
            )
            return False
        return True

    async def _ensure_coordinator(self) -> bool:
        allowed_users = set(self.config.coordinators + self.config.admins)
        if self.event.sender not in allowed_users:
            await send_text_to_room(
                self.client,
                self.room.room_id,
                TEXT_PERMISSION_DENIED,
            )
            return False
        return True

    async def process(self):
        """Process the command"""
        if self.command.startswith("echo"):
            await self._echo()
        elif self.command.startswith("help"):
            await self._show_help()
        elif self.command.startswith("invite"):
            await self._invite()
        elif self.command.startswith("rooms"):
            await self._rooms()
        else:
            await self._unknown_command()

    async def _echo(self):
        """Echo back the command's arguments"""
        response = " ".join(self.args)
        await send_text_to_room(self.client, self.room.room_id, response)

    async def _invite(self):
        """Handle an invite command"""
        if not await self._ensure_coordinator():
            return
        if not self.args:
            text = "Need more information. Either specify a room alias to invite you to or room and users to invite " \
                   "someone else to. Requires coordinator privileges.\n" \
                   "\n" \
                   "Examples:\n" \
                   "\n" \
                   "Invite yourself to a room maintained by the bot:\n" \
                   "\n" \
                   "  *invite #room:example.com*\n" \
                   "\n" \
                   "Invite one or more users to a room maintained by the bot:\n" \
                   "\n" \
                   "  *invite #room:example.com @user1:example.com @user2:example.org*"
            await send_text_to_room(self.client, self.room.room_id, text)
            return
        if not self.args[0].startswith("#"):
            await send_text_to_room(
                self.client,
                self.room.room_id,
                f"That first argument doesn't look like a room alias.",
            )
            return

        room_id = self.store.get_room_id(self.args[0])
        if not room_id:
            await send_text_to_room(
                self.client,
                self.room.room_id,
                f"Could not find room ID in my database for room {self.args[0]}",
            )
            return

        if len(self.args) == 1:
            await invite_to_room(self.client, room_id, self.event.sender, self.room.room_id, self.args[0])
            return
        else:
            for counter, user_id in enumerate(self.args, 1):
                if counter == 1:
                    # Skip the room ID
                    continue
                try:
                    check_user_id(user_id)
                except ValueError:
                    await send_text_to_room(
                        self.client,
                        self.room.room_id,
                        f"Invalid user mxid: {user_id}",
                    )
                else:
                    await invite_to_room(self.client, room_id, user_id, self.room.room_id, self.args[0])
            return

    async def _show_help(self):
        """Show the help text"""
        if not self.args:
            text = ("Hello, I am a bot made with matrix-nio! Use `help commands` to view "
                    "available commands.")
            await send_text_to_room(self.client, self.room.room_id, text)
            return

        topic = self.args[0]
        if topic == "rules":
            text = "These are the rules!"
        elif topic == "commands":
            text = "Available commands"
        else:
            text = "Unknown help topic!"
        await send_text_to_room(self.client, self.room.room_id, text)

    async def _rooms(self):
        """List and operate on rooms"""
        if not await self._ensure_coordinator():
            return
        if not self.args:
            text = "I currently maintain the following rooms:\n\n"
            results = self.store.cursor.execute("""
                select * from rooms
            """)
            rooms_list = []
            rooms = results.fetchall()
            for room in rooms:
                rooms_list.append(f"* {room[1]} / #{room[2]}:{self.config.server_name} / {room[3]}\n")
            text += "".join(rooms_list)
        else:
            text = "Unknown subcommand!"
        await send_text_to_room(self.client, self.room.room_id, text)

    async def _unknown_command(self):
        await send_text_to_room(
            self.client,
            self.room.room_id,
            f"Unknown command '{self.command}'. Try the 'help' command for more information.",
        )
