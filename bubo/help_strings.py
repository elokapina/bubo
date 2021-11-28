HELP_HELP = """Hello, I'm Bubo, a bot made with matrix-nio!

Available commands:

* breakout - Create a breakout room
* communities - List and manage communities
* invite - Invite one or more users to a room
* power - Set power levels in rooms
* rooms - List and manage rooms
* users - List and manage users and signup links
                   
More help on commands or subcommands using 'help' as the next parameter.
                   
For source code, see https://github.com/elokapina/bubo
"""

HELP_INVITE = """"Invite to rooms.

When given with only a room alias or ID parameter, invites you to that room.

To invite other users, give one or more user ID's (separated by a space) after
the room alias or ID. 

Examples:

* Invite yourself to a room:

  `invite #room:example.com
                   
* Invite one or more users to a room:
                   
  `invite #room:example.com @user1:example.com @user2:example.org`
  
Requires bot coordinator privileges. The bot must be in the room
and with power to invite users.  
"""

HELP_ROOMS = """Maintains rooms.

When given without parameters, Bubo will tell you about the rooms it maintains.

Subcommands:

* `create`

  Create a room using Bubo. Syntax:

  `rooms create NAME ALIAS TITLE ENCRYPTED(yes/no) PUBLIC(yes/no)`
    
  Example:

  `rooms create "My awesome room" epic-room "The best room ever!" yes no`
    
  Note, ALIAS should only contain lower case ascii characters and dashes. ENCRYPTED and PUBLIC are either 'yes' or 'no'.

* `list`

  Same as without a subcommand, Bubo will tell you all about the rooms it maintains.

* `list-no-admin`

  List any rooms Bubo maintains where Bubo lacks admin privileges. 
  
* `recreate`

  Recreate the current room.
  
* `unlink`

  Remove the room from Bubo's room database. The only parameter is a room ID or alias.
  
* `unlink-and-leave`

  Remove the room from Bubo's room database, then leave the room. The only parameter is a room ID or alias.
"""

HELP_ROOMS_RECREATE = """Recreates a room.

This command is useful for example if the room has no admins. It will recreate the room using the bot,
which means there will again be an admin in the room. Local members will be force joined to the room if
the bot has server admin permissions on a Synapse server. Otherwise invitations will be used to get users
to the new room.

Requires bot administrator permissions.

First issue this command without any parameters. Then issue it again with the `confirm` parameter within ten seconds.
This action cannot be reversed so care should be taken.
"""

HELP_ROOMS_RECREATE_CONFIRM = """Please confirm room re-create with the command `%srooms recreate confirm`.
You have 60s to confirm before this request expires.

**This is destructive, the room will be replaced. This cannot be reversed!**
"""

HELP_ROOMS_UNLINK = """Give the room ID or alias to unlink as the first parameter. For example:

`unlink #myroom:domain.tld`

To also make Bubo leave the room, use the `unlink-and-leave` command variant.
"""

HELP_USERS = """List or manage users.

Without any subcommands, lists users. Other subcommands:

* `create` - Create one or more users.

For help on subcommands, give the subcommand with a "help" parameter.
"""

HELP_USERS_CREATE = """Create one or more users.

Takes one or more email address as parameters. Creates the users in the identity provider,
marking their emails as verified. Then sends them an email with a password reset link.
"""

HELP_USERS_INVITE = """Invite one or more users.

Takes one or more email address as parameters. Creates a self-registration page for each user
and sends the user a link to it.
"""

HELP_USERS_KEYCLOAK_DISABLED = "The users command is not configured on this instance, sorry."

HELP_USERS_KEYCLOAK_SIGNUP_DISABLED = "The users invite and signup link commands are not configured " \
                                      "on this instance, sorry."

HELP_USERS_SIGNUPLINK = """Create a self-service signup link to send to new users.

Creates a unique signup link. The link will have a configured amount of maximum signups and validity days. Usage:

`users signuplink <maxsignups> <days>`

For example `users signupslink 50 7` would create a link for a maximum of 50 signups and with a validity period
of 7 days.
"""
