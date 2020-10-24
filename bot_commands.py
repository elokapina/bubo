import csv
import logging

# noinspection PyPackageRequirements
from nio.schemas import check_user_id

from chat_functions import send_text_to_room, invite_to_room
from communities import ensure_community_exists
from rooms import ensure_room_exists, create_breakout_room

logger = logging.getLogger(__name__)

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
        if self.command.startswith("breakout"):
            await self._breakout()
        elif self.command.startswith("communities"):
            await self._communities()
        elif self.command.startswith("help"):
            await self._show_help()
        elif self.command.startswith("invite"):
            await self._invite()
        elif self.command.startswith("rooms"):
            await self._rooms()
        else:
            await self._unknown_command()

    async def _breakout(self):
        """Create a breakout room"""
        help_text = "Creates a breakout room. Usage:\n" \
                    "\n" \
                    "breakout TOPIC PUBLIC(yes/no) ENCRYPTED(yes/no)\n" \
                    "\n" \
                    "For example:\n" \
                    "\n" \
                    "breakout \"Strategy discussion\" yes no\n" \
                    "\n" \
                    "The user requesting the breakout room will be automatically invited to the new room " \
                    "and made admin. " \
                    "If the room is public, an alias will be automatically created and posted to the room " \
                    "where the breakout command was issued. Other users can react to this message with a 👍 to " \
                    "get invited to the room. If the room is public, anyone can of course join via the alias."
        if not self.args or self.args[0] == "help":
            text = help_text
        elif self.args:
            args = self.args[1:]
            params = csv.reader([' '.join(args)], delimiter=" ")
            params = [param for param in params][0]
            if len(params) != 3:
                text = help_text
            else:
                breakout_room = await create_breakout_room(
                    params[0],
                    True if params[1] == "yes" else False,
                    True if params[2] == "yes" else False,
                    self.client,
                    self.event.sender,
                )
                text = f"Breakout room for '{params[0]}' created!\n"
                if breakout_room["alias"]:
                    text += f"\n\nJoin via {breakout_room['alias']}.\n"
                text += "\n\nReact to this message with a 👍 to get invited to the room."
                if params[2] == "yes":
                    text += " Please note due to the room being encrypted, history will not be visible to users " \
                            "until they get invited to the room."
                event_id = await send_text_to_room(self.client, self.room.room_id, text)
                if event_id:
                    self.store.store_breakout_room(event_id, breakout_room["room_id"])
                text = "*Error: failed to store breakout room data. The room was created, " \
                       "but invites via reactions will not work."
                await send_text_to_room(self.client, self.room.room_id, text)
                return
        else:
            text = "Unknown subcommand! Try `breakout help`"
        await send_text_to_room(self.client, self.room.room_id, text)

    async def _breakout_reaction(self):
        # TODO implement
        pass

    async def _communities(self):
        """List and operate on communities"""
        if not await self._ensure_coordinator():
            return
        if self.args:
            if self.args[0] == "create":
                # Create a community
                # Figure out the actual parameters
                args = self.args[1:]
                params = csv.reader([' '.join(args)], delimiter=" ")
                params = [param for param in params][0]
                if len(params) != 3 or params[0] == "help":
                    text = "Wrong number of arguments. Usage:\n" \
                           "\n" \
                           "`communities create NAME ALIAS TITLE`\n" \
                           "\n" \
                           "For example:\n" \
                           "\n" \
                           "communities create \"My epic community\" epic-community \"The best community ever!\"\n" \
                           "\n" \
                           "Note, ALIAS should only contain lower case ascii characters and dashes (maybe)."
                else:
                    result, error = await ensure_community_exists(
                        (None, params[0], params[1], params[2], None, None),
                        self.config,
                    )
                    if result == "created":
                        text = f"Community {params[0]} (+{params[1]}:{self.config.server_name}) " \
                               f"created successfully."
                        self.store.store_community(params[0], params[1], params[2])
                    elif result == "exists":
                        text = f"Sorry! Community {params[0]} (+{params[1]}:{self.config.server_name}) " \
                               f"already exists."
                    else:
                        text = f"Error creating community: {error}"
            else:
                text = "Unknown subcommand!"
        else:
            text = "I currently maintain the following communities:\n\n"
            results = self.store.cursor.execute("""
                select * from communities
            """)
            communities = []
            dbresult = results.fetchall()
            for community in dbresult:
                communities.append(f"* {community[1]} / +{community[2]}:{self.config.server_name} / {community[3]}\n")
            text += "".join(communities)
        await send_text_to_room(self.client, self.room.room_id, text)

    async def _invite(self):
        """Handle an invite command"""
        if not await self._ensure_coordinator():
            return
        if not self.args or self.args[0] == "help":
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
            text = ("Hello, I'm Bubo, a bot made with matrix-nio! Use `help commands` to view "
                    "available commands.\n"
                    "\n"
                    "For source code, see https://github.com/elokapina/bubo")
            await send_text_to_room(self.client, self.room.room_id, text)
            return

        topic = self.args[0]
        if topic == "commands":
            text = "Available commands:\n" \
                   "\n" \
                   "* breakout - Create a breakout room\n" \
                   "* communities - List and manage communities\n" \
                   "* invite - Invite one or more users to a room\n" \
                   "* rooms - List and manage rooms" \
                   "\n" \
                   "More help on commands or subcommands using 'help' as the next parameter."
        else:
            text = "Unknown help topic!"
        await send_text_to_room(self.client, self.room.room_id, text)

    async def _rooms(self):
        """List and operate on rooms"""
        if not await self._ensure_coordinator():
            return
        if self.args:
            if self.args[0] == "create":
                # Create a rooms
                # Figure out the actual parameters
                args = self.args[1:]
                params = csv.reader([' '.join(args)], delimiter=" ")
                params = [param for param in params][0]
                if len(params) != 5 or params[3] not in ('yes', 'no') or params[3] not in ('yes', 'no') \
                        or params[0] == "help":
                    text = "Wrong number or bad arguments. Usage:\n" \
                           "\n" \
                           "`rooms create NAME ALIAS TITLE ENCRYPTED(yes/no) PUBLIC(yes/no)`\n" \
                           "\n" \
                           "For example:\n" \
                           "\n" \
                           "rooms create \"My awesome room\" epic-room \"The best room ever!\" yes no\n" \
                           "\n" \
                           "Note, ALIAS should only contain lower case ascii characters and dashes." \
                           "\n" \
                           "ENCRYPTED and PUBLIC are either 'yes' or 'no'."
                else:
                    result, error = await ensure_room_exists(
                        (None, params[0], params[1], None, params[2], None, True if params[3] == "yes" else False,
                         True if params[4] == "yes" else False, 0, ""),
                        self.client,
                        self.store,
                        self.config,
                    )
                    if result == "created":
                        text = f"Room {params[0]} (#{params[1]}:{self.config.server_name}) " \
                               f"created successfully."
                    elif result == "exists":
                        text = f"Sorry! Room {params[0]} (#{params[1]}:{self.config.server_name}) " \
                               f"already exists."
                    else:
                        text = f"Error creating room: {error}"
            elif self.args[0] == "help":
                text = "Subcommands and parameters for 'rooms':" \
                       "\n" \
                       "* `create NAME ALIAS TITLE ENCRYPTED(yes/no) PUBLIC(yes/no)`" \
                       "* `list`" \
                       "\n" \
                       "Command without parameters will list rooms."
            elif self.args[0] == "list":
                text = await self._list_rooms()
            else:
                text = "Unknown subcommand!"
        else:
            text = await self._list_rooms()
        await send_text_to_room(self.client, self.room.room_id, text)

    async def _list_rooms(self):
        text = "I currently maintain the following rooms:\n\n"
        results = self.store.cursor.execute("""
                select * from rooms
            """)
        rooms_list = []
        rooms = results.fetchall()
        for room in rooms:
            rooms_list.append(f"* {room[1]} / #{room[2]}:{self.config.server_name} / {room[3]}\n")
        text += "".join(rooms_list)
        return text

    async def _unknown_command(self):
        await send_text_to_room(
            self.client,
            self.room.room_id,
            f"Unknown command '{self.command}'. Try the 'help' command for more information.",
        )
