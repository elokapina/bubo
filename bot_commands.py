import csv
import logging

# noinspection PyPackageRequirements
from nio import RoomPutStateError
# noinspection PyPackageRequirements
from nio.schemas import check_user_id

import help_strings
from chat_functions import send_text_to_room, invite_to_room
from communities import ensure_community_exists
from rooms import ensure_room_exists, create_breakout_room, set_user_power
from users import list_users

logger = logging.getLogger(__name__)

TEXT_PERMISSION_DENIED = "I'm afraid I cannot let you do that."

HELP_POWER = """Set power level in a room. Usage:

`power <user> <room> [<level>]`

* `user` is the user ID, example `@user:example.tld`
* `room` is a room alias or ID, example `#room:example.tld`. Bot must have power to give power there.
* `level` is optional and defaults to `moderator`.

Moderator rights can be given by coordinator level users. To give admin in a room, user must be admin of the bot.
"""


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
        elif self.command.startswith("power"):
            await self._power()
        elif self.command.startswith("rooms"):
            await self._rooms()
        elif self.command.startswith("users"):
            await self._users()
        else:
            await self._unknown_command()

    async def _breakout(self):
        """Create a breakout room"""
        help_text = "Creates a breakout room. Usage:\n" \
                    "\n" \
                    "breakout TOPIC\n" \
                    "\n" \
                    "For example:\n" \
                    "\n" \
                    "breakout Bot's are cool\n" \
                    "\n" \
                    "Any remaining text after the `breakout` command will be used as the name of the room. " \
                    "The user requesting the breakout room will be automatically invited to the new room " \
                    "and made admin. " \
                    "Other users can react to the bot response message with any emoji reaction to " \
                    "get invited to the room."
        if not self.args or self.args[0] == "help":
            await send_text_to_room(self.client, self.room.room_id, help_text)
        elif self.args:
            name = ' '.join(self.args)
            logger.debug(f"Breakout room name: '{name}'")
            room_id = await create_breakout_room(
                name=name,
                client=self.client,
                created_by=self.event.sender,
            )
            text = f"Breakout room '{name}' created!\n"
            text += "\n\nReact to this message with any emoji reaction to get invited to the room."
            event_id = await send_text_to_room(self.client, self.room.room_id, text)
            if event_id:
                self.store.store_breakout_room(event_id, room_id)
            else:
                text = "*Error: failed to store breakout room data. The room was created, " \
                       "but invites via reactions will not work.*"
                await send_text_to_room(self.client, self.room.room_id, text)

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

    async def _power(self):
        """Set power in a room.

        Coordinators can set moderator power.
        Admins can set also admin power.

        # TODO this does not persist power in rooms maintained with the bot if
        `permissions.demote_users` is set to True - need to make this
        command also save the power in that case, unfortunately we don't yet have
        a database table to track configured user power in rooms and might not
        be adding such a feature anytime soon.
        """
        if not await self._ensure_coordinator():
            return

        if not self.args or self.args[0] == "help":
            text = HELP_POWER
        else:
            try:
                user_id = self.args[0]
                room_id = self.args[1]
                if room_id.startswith("#"):
                    response = await self.client.room_resolve_alias(f"{room_id}")
                    room_id = response.room_id
            except AttributeError:
                text = f"Could not resolve room ID. Please ensure room exists."
            except IndexError:
                text = f"Cannot understand arguments.\n\n{HELP_POWER}"
            else:
                try:
                    level = self.args[2]
                except IndexError:
                    level = "moderator"
                if level not in ("moderator", "admin"):
                    text = f"Level must be 'moderator' or 'admin'."
                else:
                    if level == "admin" and not await self._ensure_admin():
                        text = f"Only bot admins can set admin level power, sorry."
                    else:
                        power = {
                            "admin": 100,
                            "moderator": 50,
                        }.get(level)
                        response = await set_user_power(room_id, user_id, self.client, power)
                        if isinstance(response, RoomPutStateError):
                            text = f"Sorry, command failed.\n\n{response.message}"
                        else:
                            text = f"Power level was successfully set as requested."

        await send_text_to_room(self.client, self.room.room_id, text)

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
                   "* power - Set power levels in rooms\n" \
                   "* rooms - List and manage rooms\n" \
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
                         True if params[4] == "yes" else False, ""),
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

    async def _users(self):
        """
        Command to manage users.
        """
        if not await self._ensure_admin():
            return
        text = None
        if self.args:
            if self.args[0] == "list":
                users = await list_users(self.config)
                text = f"The following usernames were found: {', '.join([user['username'] for user in users])}"
            elif self.args[0] == "help":
                text = help_strings.HELP_USERS
            elif self.args[0] == "invite":
                if len(self.args) == 1 or self.args[1] == "help":
                    text = help_strings.HELP_USERS_INVITE
                else:
                    emails = self.args[1:]
                    emails = {email.strip() for email in emails}
                    for email in emails:
                        # TODO Validate
                        # TODO Check for existing user
                        # TODO Resolve a username from email, checking for dupes
                        # TODO Create user
                        # TODO Mark email verified
                        # TODO Trigger password reset email
                        pass
        else:
            users = await list_users(self.config)
            text = f"The following usernames were found: {', '.join([user['username'] for user in users])}"
        if not text:
            text = help_strings.HELP_USERS
        await send_text_to_room(self.client, self.room.room_id, text)
