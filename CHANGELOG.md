# Changelog

## Unreleased

### Added

* Default power levels can now be configured in config as `rooms.power_levels` (see
  sample config file). If defined, they will be used in room creation power level
  overrides. By default, they will also be enforced on old rooms, unless
  `rooms.enforce_power_in_old_rooms` is set to `false`.

### Fixed

* Don't fail to start up if `matrix.user_token` is not set (but password is).

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
