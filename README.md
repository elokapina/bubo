# Bubo

[![#bubo:elokapina.fi](https://img.shields.io/matrix/bubo:elokapina.fi.svg?label=%23bubo%3Aelokapina.fi&server_fqdn=matrix.elokapina.fi)](https://matrix.to/#/#bubo:elokapina.fi) [![docker pulls](https://badgen.net/docker/pulls/elokapinaorg/bubo)](https://hub.docker.com/r/elokapinaorg/bubo) [![License:Apache2](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Matrix bot to help with community management. Can create and maintain rooms and help with
room memberships.

Created with love and rage by [Elokapina](https://elokapina.fi) (Extinction Rebellion Finland).

[![bubo](bubo.png)](https://clash-of-the-titans.fandom.com/wiki/Bubo)

Based on [nio-template](https://github.com/anoadragon453/nio-template), a template project for Matrix bots.

## Installation

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

## Usage

### Talking to Bubo

Either prefix commands with `!bubo` (or another configured prefix) in a room Bubo is in or
start a direct chat with it. When talking with Bubo directly, you don't need
the `!bubo` prefix for commands.

### Getting Bubo into a room

Bubo will automatically join rooms it is invited to.

### Commands

#### `communities`

Maintain communities.

*NOTE: This command currently operates on the communities implemented in Synapse
without a stable spec. When communities are redesigned, this command will be ported
to work with the new style communities.*

Ensure your Synapse settings allow community creation for non-admins or make Bubo
an admin. It's probably safe, but no Bubo author will take responsibility.

With no subcommands, Bubo will tell you which communities it maintains.

Subcommands:

* `create`

Create a community. Syntax:

    communities create NAME ALIAS TITLE
    
For example:

    communities create "My epic community" epic-community "The best community ever!"
    
Note, ALIAS should only contain lower case ascii characters and dashes (maybe).

#### `help`

Shows a help! Each command can also be given a subcommand `help`, to make
Bubo kindly give some usage instructions.

#### `invite`

Invites users to rooms. Bubo must be in the room with sufficient power to be
able to do the invite.

Invite yourself to a room

    invite #room:example.com
                   
Invite one or more users to a room maintained:
                   
    invite #room:example.com @user1:example.com @user2:example.org

#### `rooms`

Maintains rooms.

When given without parameters, Bubo will tell you about the rooms it maintains.

Subcommands:

* `create`

Create a room using Bubo. Syntax:

    rooms create NAME ALIAS TITLE ENCRYPTED(yes/no) PUBLIC(yes/no)
    
Example:

    rooms create "My awesome room" epic-room "The best room ever!" yes no
    
Note, ALIAS should only contain lower case ascii characters and dashes. 
ENCRYPTED and PUBLIC are either 'yes' or 'no'.

* `list`

Same as without a subcommand, Bubo will tell you all about the rooms it maintains.

### Room power levels

Bubo is picky on who can have power in a room. All rooms that it maintains (ie the rooms
stored in it's database) will be checked on start-up and Bubo will promote or demote
users to their correct level, using the following rules:

* Users marked as `admin` in the config will get power level 50
* Users marked as `coordinator` in the config will get power level 50
* Everybody else will get power level 0

Currently it's not possible to override this on a per room basis but is likely to come.

### Room and community maintenance

When Bubo starts, it will go through the rooms and communities it maintains (see above
commands). It will currently ensure the following details are correct:

* Room or community exists (tip! you can mass-create rooms/communities by inserting them to
  the database without an ID and restarting)
* Ensure rooms marked as encrypted are encrypted
* Ensure room power levels (see above "Room power levels") 

## TODO

Add more features! Bubo wants to help you manage your community!

## License

Apache2
