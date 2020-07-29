import logging
from nio import (
    SendRetryError, RoomInviteError, AsyncClient
)
from markdown import markdown

logger = logging.getLogger(__name__)


async def invite_to_room(client: AsyncClient, room_id: str, user_id: str, command_room_id: str, room_alias: str = None):
    """Invite a user to a room"""
    response = await client.room_invite(room_id, user_id)
    if isinstance(response, RoomInviteError):
        await send_text_to_room(
            client,
            command_room_id,
            f"Failed to invite user {user_id} to room: {response.message} (code: {response.status_code})",
        )
    else:
        await send_text_to_room(
            client,
            command_room_id,
            f"Invite for {room_alias or room_id} to {user_id} done!",
        )


async def send_text_to_room(
    client,
    room_id,
    message,
    notice=True,
    markdown_convert=True
):
    """Send text to a matrix room

    Args:
        client (nio.AsyncClient): The client to communicate to matrix with

        room_id (str): The ID of the room to send the message to

        message (str): The message content

        notice (bool): Whether the message should be sent with an "m.notice" message type
            (will not ping users)

        markdown_convert (bool): Whether to convert the message content to markdown.
            Defaults to true.
    """
    # Determine whether to ping room members or not
    msgtype = "m.notice" if notice else "m.text"

    content = {
        "msgtype": msgtype,
        "format": "org.matrix.custom.html",
        "body": message,
    }

    if markdown_convert:
        content["formatted_body"] = markdown(message)

    try:
        await client.room_send(
            room_id,
            "m.room.message",
            content,
            ignore_unverified_devices=True,
        )
    except SendRetryError:
        logger.exception(f"Unable to send message response to {room_id}")

