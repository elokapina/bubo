# Bubo

[![#bubo:elokapina.fi](https://img.shields.io/matrix/bubo:elokapina.fi.svg?label=%23bubo%3Aelokapina.fi&server_fqdn=matrix.elokapina.fi)](https://matrix.to/#/#bubo:elokapina.fi) [![docker pulls](https://badgen.net/docker/pulls/elokapinaorg/bubo)](https://hub.docker.com/r/elokapinaorg/bubo) [![License:Apache2](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Matrix bot to help with community management. Can create and maintain rooms and help with
room memberships.

Created with love and rage by [Elokapina](https://elokapina.fi) (Extinction Rebellion Finland).

[![bubo](bubo.png)](https://clash-of-the-titans.fandom.com/wiki/Bubo)

Based on [nio-template](https://github.com/anoadragon453/nio-template), a template project for Matrix bots.

## Installation

### Docker (recommended)

Docker images [are available](https://hub.docker.com/r/elokapinaorg/bubo).

An example configuration file is provided as `sample.config.yaml`.

Make a copy of that, edit as required and mount it to `/config/config.yaml` on the Docker container.

You'll also need to give the container a folder for storing state. Create a folder, ensure
it's writable by the user the container process is running as and mount it to `/data`.

Example:

```bash
cp sample.config.yaml config.yaml
# Edit config.yaml, see the file for details
mkdir data
docker run -v ${PWD}/config.docker.yaml:/config/config.yaml:ro \
    -v ${PWD}/data:/data --name bubo elokapinaorg/bubo
```

### Source

* Install any system dependencies by copying what the Dockerfile does 
* Create a Python 3.8+ virtualenv
* Do `pip install -U pip setuptools pip-tools`
* Do `pip-sync`
* Copy the example `sample.config.yaml` file into `config.yaml` and edit
* Run with `python main.py config.yaml`

## Usage

### Talking to Bubo

Either prefix commands with `!bubo` (or another configured prefix) in a room Bubo is in or
start a direct chat with it. When talking with Bubo directly, you don't need
the `!bubo` prefix for commands.

### Getting Bubo into a room

Bubo will automatically join rooms it is invited to.

### Commands

#### `breakout`

Creates a breakout room. The user who requested the breakout room creation will
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

#### `groupinvite`

Invite a user to a predefined group of rooms.

Syntax:

    groupinvite @user1:domain.tld groupname [subgroups]

Where "groupname" should be replaced with the group to join to. Additionally,
subgroups can be given as well.

Groups must be configured to the Bubo configuration file by an administrator.

This command requires coordinator level permissions.

#### `help`

Shows a help! Each command can also be given a subcommand `help`, to make
Bubo kindly give some usage instructions.

#### `invite`

Invite to rooms.

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

#### `join`

Join one or more users to rooms.

Syntax:

    join !roomidoralias:domain.tld @user1:domain.tld @user2:domain.tld
    
If Bubo has Synapse admin powers, it will try to join admin API join any local users
(which still requires Bubo to be in the room and be able to invite).
Otherwise, a normal onvitation is used.

This command requires coordinator level permissions.

#### `power`

Set power level in a room. Usage:

`power <user> <room> [<level>]`

* `user` is the user ID, example `@user:example.tld`
* `room` is a room alias or ID, example `#room:example.tld`. Bot must have power to give power there.
* `level` is optional and defaults to `moderator`.

Moderator rights can be given by coordinator level users. To give admin in a room, user must be admin of the bot.

#### `rooms` and `spaces`

Maintains rooms and spaces.

When given without parameters, Bubo will tell you about the rooms or spaces it maintains.

Subcommands below.

##### `alias` - Manage room and space aliases

Manage room or space aliases.

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

##### `create` - Create room or space

Syntax:

    rooms/spaces create NAME ALIAS TITLE ENCRYPTED(yes/no) PUBLIC(yes/no)
    
Example:

    rooms/spaces create "My awesome room" epic-room "The best room ever!" yes no
    
Note, ALIAS should only contain lower case ascii characters and dashes. 
ENCRYPTED and PUBLIC are either 'yes' or 'no'.

##### `link` and `link-and-admin` - Register rooms or spaces with Bubo

Both variants make Bubo attempt to join the room or space and store the room or space in 
the database to start tracking it. If Bubo is Synapse admin and/or admin permissions is requested, 
it will also try to join and/or make itself admin using the Synapse admin API.

The only parameter is a room/space ID or alias.

##### `list` - List rooms/spaces

Same as without a subcommand, Bubo will tell you all about the rooms or spaces it maintains.

##### `list-no-admin` - List rooms/spaces without Bubo admin privileges

List any rooms or spaces Bubo maintains where Bubo lacks admin privileges. 

##### `recreate` - Recreate a room or space

Recreate a room or space. This is a bit like the room upgrade functionality in Element, but it's designed to
also work when admin power levels have been lost in the room, and thus an upgrade cannot be done.
In short the command will:

  * Create a new room mirroring the current room
  * Rename the old room with a prefix (defaults to "OLD", see config to change it)
  * Invite all room members (including those in invite status) to the new room
  * Try to force join local server members using the Synapse admin API if Bubo has
    been defined as Synapse admin in config (and of course in Synapse too)
  * Post a message to both rooms, linking them together
  * Optionally join a configured secondary admin to the room

After giving the command in the room, Bubo will ask for confirmation.

**NOTE** This command cannot be reversed so should be used with care. The old room will however
stay as it is, so in problem cases it should be enough to just rename the old room back.

This command requires Bubo admin privileges. It does not require Bubo to have any special power
in the room to be recreated.
 
##### `unlink` - Unregister a room or space

  Remove the room or space from Bubo's room database. The only parameter is a room/space ID or alias.
  
##### `unlink-and-leave` - Unregister a room or space, and leave it

  Remove the room or space from Bubo's room database, then leave the room or space. 
  The only parameter is a room/space ID or alias.

#### `users`

Manage users of an identity provider.

Currently [Keycloak](https://www.keycloak.org/) is the only identity provider supported.
See `sample.config.yaml` for how to configure a Keycloak client.

Subcommands:

##### `list` (or no subcommand)

  List currently registered users. Requires admin level permissions.

##### `create`

  Creates users for the given emails and sends them a password reset email. The users
  email will be marked as verified. Give one or more emails as parameters. Requires admin level permissions.

##### `invite`
  
  Send an invitation to the email(s) given for self-registration. Requires
  an instance of [keycloak-signup](https://github.com/elokapina/keycloak-signup).
  The invitation will contain a one-time link valid for 7 days. Requires coordinator level permissions.

##### `rooms`

List the rooms of a user.

Usage:

    users rooms @user:domain.tld
    
Requires bot admin permissions. Bubo must also be a Synapse admin.

##### `signuplink`

  Create a self-service signup link with a chosen amount of maximum signups
  and days of validity. Requires an instance of 
  [keycloak-signup](https://github.com/elokapina/keycloak-signup).
  Requires coordinator level permissions.

### Room power levels

#### User power

Bubo can be picky on who can have power in a room. All rooms that it maintains (ie the rooms
stored in it's database) will be checked on start-up and Bubo can be made to promote or demote
users to their correct level, using the following rules:

* Users marked as `admin` in the config will get power level 50, if in the room
* Users marked as `coordinator` in the config will get power level 50, if in the room
* Everybody else will get power level 0

Bubo can be told to not demote or promote users in the config. By default it will 
promote but not demote users in the room. Users not in the room who have too much power
will always be demoted.

Currently it's not possible to override this on a per room basis but is likely to come.

#### Room power defaults

The sample config contains `room.power_levels` for the default power levels that
Bubo will use for new rooms. By default, it will also enforce these power levels on
old rooms, unless told not to.

### Room and space maintenance

When Bubo starts, it will go through the rooms and spaces it maintains (see above
commands). It will currently ensure the following details are correct:

* Room or space exists (tip! you can mass-create rooms/spaces by inserting them to
  the database without an ID and restarting)
* Ensure rooms/spaces marked as encrypted are encrypted
* Ensure room/spaces power levels (see above "Room power levels") 

## Development

If you need help or want to otherwise chat, jump to `#bubo:elokapina.fi`!

### Dependencies

* Create a Python 3.10+ virtualenv
* Do `pip install -U pip setuptools pip-tools`
* Do `pip-sync`

To update dependencies, do NOT edit `requirements.txt` directly. Any changes go into
`requirements.in` and then you run `pip-compile`. If you want to upgrade existing
non-pinned (in `requirements.in`) dependencies, run `pip-compile --upgrade`, keeping
the ones that you want to update in `requirements.txt` when commiting. See more info
about `pip-tools` at https://github.com/jazzband/pip-tools


### Releasing

* Update `CHANGELOG.md`
* Commit changelog
* Make a tag
* Push the tag
* Make a GitHub release, copy the changelog for the release there
* Build a docker image
  * `docker build . -t elokapinaorg/bubo:v<version>`
* Push docker image
* Update topic in `#bubo:elokapina.fi`
* Consider announcing on `#thisweekinmatrix:matrix.org` \o/

## TODO

Add more features! Bubo wants to help you manage your community!

## License

Apache2
