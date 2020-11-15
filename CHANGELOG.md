# Changelog

## Unreleased

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
