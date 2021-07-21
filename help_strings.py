HELP_USERS = """List or manage users.

Without any subcommands, lists users. Other subcommands:

* `create` - Create one or more users.

For help on subcommands, give the subcommand with a "help" parameter.
"""

HELP_USERS_CREATE = """Create one or more users.

Takes one or more email address as parameters. Creates the users in the identity provider,
marking their emails as verified. Then sends them an email with a password reset link.
"""
