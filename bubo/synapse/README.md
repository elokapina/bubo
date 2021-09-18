# Synapse modules

This folder contains some Synapse modules.

Might be packaged at some point, but for now it's best just to copy the module file as is
into the Synapse Python path. This isn't currently meant to be used as a package.

See https://matrix-org.github.io/synapse/latest/modules.html on how Synapse
modules work.

### deny_events.DenyEventsModule

Denies events and invitations forHaven configured rooms by ID.

Config:

```yaml
rooms:
  - "!foobar:domain.tld"
  - "!barfoo:domain.tld"
```
