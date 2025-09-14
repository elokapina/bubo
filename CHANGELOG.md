# Changelog

## unreleased

### Breaking changes

* Always require a command prefix even in direct messages. This change is due to
  issues matrix-nio has sometimes recognizing whether the room is a dm or a group.

### Added

* Add `spaces` command. Mirrors `rooms` command for subcommands and functionality, with the 
  exception that the created room will be of type Space.

* Added rooms `link` and `link-and-admin` subcommands. Both variants make Bubo attempt
  to join the room and store the room in the database to start tracking it. If Bubo
  is Synapse admin and/or admin permissions is requested, it will also try to join and/or
  make itself admin using the Synapse admin API.

* Add `rooms` subcommand `alias`. Allows maintaining aliases for rooms, including
  adding, removing and setting the main alias.

* Add `join` command, which allows (Synapse admin) force joining users to rooms or as 
  a fallback inviting users to rooms.

* Add `groupinvite` command, which allows inviting a user to a group
  of rooms. Room groups are preconfigured in the config file.

* Add `users` subcommand `rooms`. Lists users rooms on the server Bubo is installed on.
  Requires Bubo being Synapse admin and also requires Bubo admin permissions.

* Added `pindora` command to manage Pindora keys.

### Changed

* Allow removing room encryption by recreating with `rooms recreate-unencrypted` command.

* The `invite` command will now check the user exists before sending an invitation.

* Use `pip-tools` to lock dependencies.

* Docker image is now Python 3.10.

### Fixed

* Force `charset_normalizer` dependency logs to `warning` level to avoid spammy info
  logs about probing the chaos when the Matrix server is unavailable.

* Fixed incorrect check for invalid coordinator room / user ID's when loading config ([#17](https://github.com/elokapina/bubo/pull/17)).

* Fixed config check failing in the case that the default is `False` and config is not required.

### Removed

* Removed any attempts to maintain room encryption for old rooms on startup. This code
  seems to have been broken and seems like a footgun waiting to happen. It should
  be replaced with a manual "encrypt room" command if needed.

* Removed the `communities` command. Existing configured communities will not be tracked.

## v0.3.0 - 2022-01-23

### Added

* Default power levels can now be configured in config as `rooms.power_levels` (see
  sample config file). If defined, they will be used in room creation power level
  overrides. By default, they will also be enforced on old rooms, unless
  `rooms.enforce_power_in_old_rooms` is set to `false`.

* Add config option `callbacks.unable_to_decrypt_responses` to allow disabling
  the room reply to messages that Bubo cannot decrypt.
  
* Add command `power` to set power levels in a room where the bot has the 
  required power.
  
* Add command `users` to interact with an identity provider. Currently, only Keycloak
  is supported. Supported features is listing, creating and inviting new users.
  Created users will be sent a password reset email, and their email will be
  marked as verified. Invitation allows the invited user to choose their own username.
  Support also exists for creating self-service signup links.

  Note, the invite and self-service signup link creation commands 
  require an instance of [keycloak-signup](https://github.com/elokapina/keycloak-signup).

* Logging to a Matrix room is now possible. User access token must be set for the logging
  to be used.

* Allow configuring admins and coordinators based on room membership. Both config lists
  now accept a room ID whose members will be added as admins or coordinators when checking
  access rights for commands or when setting power levels in rooms.

* Added rooms `list-no-admin` subcommand. Lists all the rooms that Bubo should be maintaining,
  but which is lacks admin rights to do so for.

* Added rooms `recreate` subcommand. Recreates a room, specifically designed for the case where
  admin permissions have been lost and a new room is needed.

* Added rooms `unlink` and `unlink-and-leave` subcommands. The first variant unlinks a room
  tracked by Bubo, the second also leaves the room.

* When receiving an event the bot cannot decrypt, the event will now be stored for
  later. When keys are received later matching any stored encrypted events, a new attempt
  will be made to decrypt them.

### Changed

* Message edits are now understood as new commands from clients that send them 
  prefixed with ` * ` (for example Element).

* Invite command no longer requires room to be maintained by Bubo. It's enough now that
  Bubo is in the room and able to invite to it. It also now works with room ID in
  addition to alias.

* Produce a more useful log error when Bubo fails to decrypt an event.

### Fixed

* Don't fail to start up if `matrix.user_token` is not set (but password is).

* Don't crash in `set_user_power` if bot not in room. 

### Deprecated

* Communities support is deprecated. The `communities` command will be removed in Bubo v0.4.0.

### Removed

* Removed the `power_to_write` override in the `rooms` database table. Rooms
  can no longer for now have custom power levels enforced by Bubo on a per room basis.  

## v0.2.0 - 2020-10-30

### Added

* New command `breakout`. Allows splitting discussion into breakout rooms.

## v0.1.0 - 2020-10-24

Initial version with the following commands:
* rooms (list and create)
* communities (list and create)
* invite (self or others)
