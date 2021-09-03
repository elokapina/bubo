import smtplib
import ssl

from bubo.config import Config


def send_plain_email(config: Config, receiver: str, message: str):
    auth = config.email.get("auth")
    context = ssl.create_default_context()
    host = config.email.get("host")
    password = auth.get("password")
    port = config.email.get("port")
    sender = config.email.get("sender")
    username = auth.get("username")
    if config.email.get("ssl"):
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            if auth:
                server.login(username, password)
            server.sendmail(sender, receiver, message)
    elif config.email.get("starttls"):
        with smtplib.SMTP(host, port) as server:
            server.starttls(context=context)
            if auth:
                server.login(username, password)
            server.sendmail(sender, receiver, message)
    else:
        raise Exception("Refusing to send non-secure emails")
