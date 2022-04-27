import asyncio
import logging
import time
import uuid
from typing import Optional

import aiohttp
# noinspection PyPackageRequirements
from nio import (
    SendRetryError, RoomInviteError, AsyncClient, ErrorResponse, RoomSendResponse,
)
from markdown import markdown

from bubo.config import Config
from bubo.utils import get_request_headers

logger = logging.getLogger(__name__)


async def invite_to_room(
    client: AsyncClient, room_id: str, user_id: str, command_room_id: str = None, room_alias: str = None,
    ignore_in_room: bool = False,
):
    """Invite a user to a room"""
    response = await client.room_invite(room_id, user_id)
    if isinstance(response, RoomInviteError):
        if response.status_code == "M_LIMIT_EXCEEDED":
            time.sleep(3)
            await invite_to_room(client, room_id, user_id, command_room_id, room_alias)
            return
        if command_room_id:
            if ignore_in_room and response.message.find("is already in the room") > -1:
                await send_text_to_room(
                    client,
                    command_room_id,
                    f"{user_id} already in room {room_alias or room_id}",
                )
                return
            await send_text_to_room(
                client,
                command_room_id,
                f"Failed to invite user {user_id} to room: {response.message} (code: {response.status_code})",
            )
            logger.warning(f"Failed to invite user {user_id} to room: {response.message} "
                           f"(code: {response.status_code})")
    elif command_room_id:
        await send_text_to_room(
            client,
            command_room_id,
            f"Invite for {room_alias or room_id} to {user_id} done!",
        )
        logger.info(f"Invite for {room_alias or room_id} to {user_id} done!")


async def send_text_to_room(
    client,
    room_id,
    message,
    notice=True,
    markdown_convert=True,
    reply_to_event_id: Optional[str] = None,
) -> str:
    """Send text to a matrix room.

    Args:
        client (nio.AsyncClient): The client to communicate to matrix with

        room_id (str): The ID of the room to send the message to

        message (str): The message content

        notice (bool): Whether the message should be sent with an "m.notice" message type
            (will not ping users).

        markdown_convert (bool): Whether to convert the message content to markdown.
            Defaults to true.

        reply_to_event_id: Whether this message is a reply to another event. The event
            ID this is message is a reply to.
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

    if reply_to_event_id:
        content["m.relates_to"] = {"m.in_reply_to": {"event_id": reply_to_event_id}}

    try:
        response = await client.room_send(
            room_id,
            "m.room.message",
            content,
            ignore_unverified_devices=True,
        )
        if isinstance(response, ErrorResponse):
            if response.status_code == "M_LIMIT_EXCEEDED":
                time.sleep(3)
                return await send_text_to_room(client, room_id, message, notice, markdown_convert)
            else:
                logger.warning(f"Failed to send message to {room_id} due to {response.status_code}")
        elif isinstance(response, RoomSendResponse):
            return response.event_id
        else:
            logger.warning(f"Failed to get event_id from send_text_to_room, response: {response}")
    except SendRetryError:
        logger.exception(f"Unable to send message to {room_id}")


async def send_text_to_room_c2s(
    config: Config,
    room_id: str,
    message: str,
    notice=True,
    markdown_convert=True,
    reply_to_event_id: Optional[str] = None,
) -> str:
    """
    Send text to a matrix room using the C2S API directly.
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

    if reply_to_event_id:
        content["m.relates_to"] = {"m.in_reply_to": {"event_id": reply_to_event_id}}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{config.homeserver_url}/_matrix/client/r0/rooms/{room_id}/send/m.room.message/{str(uuid.uuid4())}",
                json=content,
                headers=get_request_headers(config),
            ) as response:
                if response.status == 429:
                    await asyncio.sleep(3)
                    return await send_text_to_room_c2s(
                        config, room_id, message, notice, markdown_convert, reply_to_event_id,
                    )
                response.raise_for_status()
                return (await response.json())["event_id"]
    except Exception as ex:
        logger.exception(f"Unable to send C2S message to {room_id}: {ex}")
