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