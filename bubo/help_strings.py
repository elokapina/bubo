HELP_HELP = """Hello, I'm Bubo, a bot made with matrix-nio!

Available commands:

* breakout - Create a breakout room
* groupinvite - Invite a pre-defined group to a room
* groupjoin - Alias for `groupinvite`
* invite - Invite one or more users to a room
* join - Join a user to a room
* power - Set power levels in rooms
* rooms - List and manage rooms
* spaces - List and manage spaces
* users - List and manage users and signup links
                   
More help on commands or subcommands using 'help' as the next parameter.
                   
For source code, see https://github.com/elokapina/bubo
"""

HELP_BREAKOUT = """Creates a breakout room. The user who requested the breakout room creation will
automatically be invited to the room and made admin. The room will be created
as non-public and non-encrypted.

Other users can react to the breakout room creation response with any emoji reaction to
get an invite to the room.

Syntax:

    breakout TOPIC
    
For example:

    breakout How awesome is Bubo?
    
Any remaining text after `breakout` will be used as the room name.

Note that while Bubo will stay in the breakout room itself, it will not maintain
it in any way like the rooms created using the `rooms` command.
"""

HELP_GROUPINVITE = """Invite a user to a predefined group of rooms.

Syntax:

    groupinvite @user1:domain.tld groupname [subgroups]

Where "groupname" should be replaced with the group to join to. Additionally,
subgroups can be given as well.

Groups must be configured to the Bubo configuration file by an administrator.

This command requires coordinator level permissions.
"""

HELP_INVITE = """"Invite to rooms.

When given with only a room alias or ID parameter, invites you to that room.

To invite other users, give one or more user ID's (separated by a space) after
the room alias or ID. 

Examples:

* Invite yourself to a room:

  `invite #room:example.com`
                   
* Invite one or more users to a room:
                   
  `invite #room:example.com @user1:example.com @user2:example.org`
  
Requires bot coordinator privileges. The bot must be in the room
and with power to invite users.  
"""

HELP_JOIN = """Join one or more users to rooms.

Syntax:

    join !roomidoralias:domain.tld @user1:domain.tld @user2:domain.tld
    
If Bubo has Synapse admin powers, it will try to join admin API join any local users
(which still requires Bubo to be in the room and be able to invite).
Otherwise, a normal onvitation is used.

This command requires coordinator level permissions.
"""

HELP_POWER = """Set power level in a room. Usage:

`power <user> <room> [<level>]`

* `user` is the user ID, example `@user:example.tld`
* `room` is a room alias or ID, example `#room:example.tld`. Bot must have power to give power there.
* `level` is optional and defaults to `moderator`.

Moderator rights can be given by coordinator level users. To give admin in a room, user must be admin of the bot.
"""

HELP_ROOMS_AND_SPACES = """Maintains %%TYPES%%.

When given without parameters, Bubo will tell you about the %%TYPES%% it maintains.

Subcommands:

* `alias`

  Add, remove or set main canonical alias for a %%TYPE%%.
  
  Examples:
  
  To add an alias to a %%TYPE%%:
  
  `%%TYPES%% alias !roomidoralias:domain.tld add #alias:domain.tld`
  
  To make an alias the main canonical alias for a %%TYPE%% (the alias must exist):
  
  `%%TYPES%% alias !roomidoralias:domain.tld main #alias:domain.tld`
  
  To remove an alias from a %%TYPE%%:
  
  `%%TYPES%% alias !roomidoralias:domain.tld remove #alias:domain.tld`

* `create`

  Create a %%TYPE%% using Bubo. Syntax:

  `%%TYPES%% create NAME ALIAS TITLE ENCRYPTED(yes/no) PUBLIC(yes/no)`
    
  Example:

  `%%TYPES%% create "My awesome room" epic-room "The best room ever!" yes no`
    
  Note, ALIAS should only contain lower case ascii characters and dashes. ENCRYPTED and PUBLIC are either 'yes' or 'no'.

* `link`

  Add a %%TYPE%% to the Bubo database to start tracking it. Will try to join the %%TYPE%% if not a member.
  The %%TYPE%% must have an alias. Usage:
  
  `link #room-alias:domain.tld`
  
* `link-and-admin`

  Same as link but will force join through a local user and make Bubo an admin if configured as Synapse admin. Usage:
  
  `link-and-admin #room-alias:domain.tld`  

* `list`

  Same as without a subcommand, Bubo will tell you all about the %%TYPES%% it maintains.

* `list-no-admin`

  List any %%TYPES%% Bubo maintains where Bubo lacks admin privileges. 
  
* `recreate`

  Recreate the current %%TYPE%%.
  
* `unlink`

  Remove the %%TYPE%% from Bubo's %%TYPE%% database. The only parameter is a %%TYPE%% ID or alias.
  
* `unlink-and-leave`

  Remove the %%TYPE%% from Bubo's %%TYPE%% database, then leave the %%TYPE%%. The only parameter is a %%TYPE%% ID or 
  alias.
"""

HELP_ROOMS = HELP_ROOMS_AND_SPACES.replace("%%TYPES%%", "rooms").replace("%%TYPE%%", "room")
HELP_SPACES = HELP_ROOMS_AND_SPACES.replace("%%TYPES%%", "spaces").replace("%%TYPE%%", "space")

HELP_ROOMS_ALIAS = """Manage room or space aliases.

Allows adding and removing aliases, and setting the main (canonical) alias of a room or space.

Format:

    rooms/spaces alias !roomidoralias:domain.tld subcommand #alias:domain.tld
    
Where "subcommand" can be one of: "add", "remove", "main".

Examples:

    rooms/spaces alias !roomidoralias:domain.tld add #alias:domain.tld 
    rooms/spaces alias !roomidoralias:domain.tld remove #alias:domain.tld 
    rooms/spaces alias !roomidoralias:domain.tld main #alias:domain.tld
    
Notes:

* "remove" cannot remove the main alias. First add another alias and set it main alias.
* "main" can only handle aliases for the same domain Bubo runs on currently. This may change in the future.

This command requires coordinator level permissions.
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
You have 300s to confirm before this request expires.

**This is destructive, the room will be replaced. This cannot be reversed!**
"""

HELP_ROOMS_UNLINK = """Give the room ID or alias to unlink as the first parameter. For example:

`unlink #myroom:domain.tld`

To also make Bubo leave the room, use the `unlink-and-leave` command variant.
"""

HELP_ROOMS_LINK = """Store an existing room in Bubo's database. 
Give the room ID or alias to link as the first parameter. For example:

`link #myroom:domain.tld`

Bubo will try to join the room, using the admin API if normal join fails.
"""

HELP_ROOMS_LINK_AND_ADMIN = """Store an existing room in Bubo's database. 
Also try to make Bubo an admin of the room, if Bubo is server admin.  
Give the room ID or alias to link as the first parameter. For example:

`link-and-admin #myroom:domain.tld`

Bubo will try to join the room, using the admin API if normal join fails.
If necessary, it will use the admin API to make an admin of the room make
itself admin.
"""

HELP_USERS = """List or manage users.

Without any subcommands, lists users. Other subcommands:

* `create` - Create one or more Keycloak users.

* `list` - Lists users in Keycloak.

* `invite` - Send a a Keycloak Signup invitation link to a user.

* `rooms` - List rooms of a Matrix user.

* `signuplink` - Create a signup link with Keycloak Signup.

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

HELP_USERS_ROOMS = """List the rooms of a user.

Usage:

    users rooms @user:domain.tld
    
Requires bot admin permissions. Bubo must also be a Synapse admin.
"""

HELP_USERS_SIGNUPLINK = """Create a self-service signup link to send to new users.

Creates a unique signup link. The link will have a configured amount of maximum signups and validity days. Usage:

`users signuplink <maxsignups> <days>`

For example `users signupslink 50 7` would create a link for a maximum of 50 signups and with a validity period
of 7 days.
"""
