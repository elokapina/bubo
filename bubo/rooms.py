import asyncio
import logging
import time
from copy import deepcopy
from typing import Tuple, Optional, List, Dict, Union

import aiohttp
from aiohttp import ClientResponse
# noinspection PyPackageRequirements
from nio import (
    AsyncClient, RoomVisibility, EnableEncryptionBuilder, RoomPutStateError, RoomGetStateEventError,
    RoomPutStateResponse, RoomGetStateEventResponse, MatrixRoom, RoomCreateError, RoomInviteError,
)
# noinspection PyPackageRequirements
from nio.http import TransportResponse

from bubo import synapse_admin
from bubo.chat_functions import invite_to_room, send_text_to_room, send_text_to_room_c2s
from bubo.config import Config
from bubo.storage import Storage
from bubo.utils import with_ratelimit, get_users_for_access

logger = logging.getLogger(__name__)


async def create_breakout_room(
    name: str, client: AsyncClient, created_by: str
) -> Dict:
    """
    Create a breakout room.
    """
    logger.info(f"Attempting to create breakout room '{name}'")
    response = await with_ratelimit(
        client,
        "room_create",
        name=name,
        visibility=RoomVisibility.private,
    )
    if getattr(response, "room_id", None):
        room_id = response.room_id
        logger.info(f"Breakout room '{name}' created at {room_id}")
    else:
        raise Exception(f"Could not create breakout room: {response.message}, {response.status_code}")
    await set_user_power(room_id, created_by, client, 100)
    await invite_to_room(client, room_id, created_by)
    return room_id


async def ensure_room_encrypted(room_id: str, client: AsyncClient):
    """
    Ensure room is encrypted.
    """
    state = await client.room_get_state_event(room_id, "m.room.encryption")
    if state.content.get('errcode') == 'M_NOT_FOUND':
        event_dict = EnableEncryptionBuilder().as_dict()
        response = await client.room_put_state(
            room_id=room_id,
            event_type=event_dict["type"],
            content=event_dict["content"],
        )
        if isinstance(response, RoomPutStateError):
            if response.status_code == "M_LIMIT_EXCEEDED":
                time.sleep(3)
                return ensure_room_encrypted(room_id, client)


async def delete_user_room_tag(
    config: Config, session: aiohttp.ClientSession, user: str, room_id: str, token: str, tag: str,
) -> bool:
    async with session.delete(
            f"{config.homeserver_url}/_matrix/client/r0/user/{user}/rooms/{room_id}/tags/{tag}",
            headers={
                "Authorization": f"Bearer {token}",
            },
    ) as response:
        if response.status == 429:
            await asyncio.sleep(1)
            return await delete_user_room_tag(config, session, user, room_id, token, tag)
        try:
            response.raise_for_status()
            logger.debug("Delete room tag for user: %s, %s, %s", user, room_id, tag)
            return True
        except Exception as ex:
            logger.warning("Failed to delete room tag %s for user %s for room %s: %s", tag, user, room_id, ex)
            return False


async def ensure_room_power_levels(
        room_id: str, client: AsyncClient, config: Config, members: List,
):
    """
    Ensure room has correct power levels.
    """
    logger.debug(f"Ensuring power levels: {room_id}")
    state, users = await get_room_power_levels(client, room_id)
    member_ids = {member.user_id for member in members}
    coordinators = await get_users_for_access(client, config, "coordinators")

    # check existing users
    for mxid, level in users.items():
        if mxid == config.user_id:
            continue

        # Promote users if they need more power
        if config.permissions_promote_users:
            if mxid in coordinators and mxid in member_ids and level < 50:
                users[mxid] = 50
        # Demote users if they should have less power
        if config.permissions_demote_users:
            if mxid not in coordinators and level > 0:
                users[mxid] = 0
        # Always demote users with too much power if not in the room
        if mxid not in member_ids:
            users[mxid] = 0

    # check new users
    if config.permissions_promote_users:
        for user in coordinators:
            if user in member_ids and user != config.user_id:
                users[user] = 50

    power_levels = config.rooms.get("power_levels") if config.rooms.get("enforce_power_in_old_rooms", True) else {}
    new_power = deepcopy(state.content)
    new_power.update(power_levels)
    new_power["users"] = users

    if state.content != new_power:
        logger.info(f"Updating room {room_id} power levels")
        response = await with_ratelimit(
            client,
            "room_put_state",
            room_id=room_id,
            event_type="m.room.power_levels",
            content=new_power,
        )
        logger.debug(f"Power levels update response: {response}")


async def ensure_room_exists(
        room: tuple, client: AsyncClient, store: Storage, config: Config, dry_run: bool = False,
) -> Tuple[str, Optional[str]]:
    """
    Maintains a room.
    """
    dbid, name, alias, room_id, title, icon, encrypted, public, room_type = room
    logger.debug(f"Ensuring room: {room}")
    room_created = False
    logger.info(f"Ensuring room {name} ({alias}) exists")
    state = []
    if encrypted:
        state.append(
            EnableEncryptionBuilder().as_dict(),
        )

    if not dbid:
        # Check if we track this room already
        db_room = store.get_room_by_alias(alias)
        if db_room:
            dbid = db_room[0]
            room_id = db_room[3]
            logger.info("Room %s found in the database as %s", name, room_id)

    if not room_id:
        # Check if room exists
        response = await client.room_resolve_alias(f"#{alias}:{config.server_name}")
        if getattr(response, "room_id", None):
            room_id = response.room_id
            logger.info(f"Room '{alias}' resolved to {room_id}")
        else:
            logger.info(f"Could not resolve room '{alias}', will try create")
            # Create room
            space = room_type == "space"
            if not dry_run:
                response = await client.room_create(
                    visibility=RoomVisibility.public if public else RoomVisibility.private,
                    alias=alias,
                    name=name,
                    topic=title,
                    initial_state=state,
                    power_level_override=config.rooms.get("power_levels"),
                    space=space,
                )
                if getattr(response, "room_id", None):
                    room_id = response.room_id
                    logger.info(f"Room '{alias}' created at {room_id}")
                    room_created = True
                else:
                    if response.status_code == "M_LIMIT_EXCEEDED":
                        # Wait and try again
                        logger.info("Hit request limits, waiting 3 seconds...")
                        time.sleep(3)
                        return await ensure_room_exists(room, client, store, config)
                    raise Exception(f"Could not create room: {response.message}, {response.status_code}")
            else:
                logger.info(f"Not creating room '{alias}' due to dry run")
        if not dry_run:
            if dbid:
                # Store room ID
                store.cursor.execute("""
                    update rooms set room_id = ? where id = ?
                """, (room_id, dbid))
                store.conn.commit()
                logger.info(f"Room '{alias}' room ID stored to database")
            else:
                store.cursor.execute("""
                    insert into rooms (
                        name, alias, room_id, title, encrypted, public, type
                    ) values (
                        ?, ?, ?, ?, ?, ?, ?
                    )
                """, (name, alias, room_id, title, encrypted, public, room_type))
                store.conn.commit()
                logger.info(f"Room '{alias}' creation stored to database")

    if encrypted and not dry_run:
        await ensure_room_encrypted(room_id, client)

        # TODO ensure room name + title
        # TODO ensure room alias

    # TODO Add rooms to communities

    if not dry_run:
        room_members = await with_ratelimit(client, "joined_members", room_id)
        members = getattr(room_members, "members", [])

        await ensure_room_power_levels(room_id, client, config, members)

    if room_created:
        return "created", None
    return "exists", None


async def get_room_power_levels(
    client: AsyncClient, room_id: str,
) -> Tuple[Optional[RoomGetStateEventResponse], Optional[Dict]]:
    logger.debug(f"Fetching power levels for {room_id}")
    state = None
    try:
        state = await with_ratelimit(client, "room_get_state_event", room_id=room_id, event_type="m.room.power_levels")
        logger.debug(f"Found power levels state: {state}")
        users = state.content["users"].copy()
    except KeyError as ex:
        logger.warning(f"Error looking for power levels for room {room_id}: {ex} - state: {state}")
        return None, None
    return state, users


async def get_user_room_tags(
    config: Config, session: aiohttp.ClientSession, user: str, room_id: str, token: str,
) -> Optional[Dict]:
    async with session.get(
        f"{config.homeserver_url}/_matrix/client/r0/user/{user}/rooms/{room_id}/tags",
        headers={
            "Authorization": f"Bearer {token}",
        },
    ) as response:
        if response.status == 429:
            await asyncio.sleep(1)
            return await get_user_room_tags(config, session, user, room_id, token)
        try:
            response.raise_for_status()
            data = await response.json()
            logger.debug("Got room tags for user: %s, %s, %s", user, room_id, data)
            return data["tags"]
        except Exception as ex:
            logger.warning("Failed to get room tags for user %s for room %s: %s", user, room_id, ex)
            return


async def get_room_directory_status(config: Config, session: aiohttp.ClientSession, room_id: str) -> Optional[str]:
    async with session.get(
        f"{config.homeserver_url}/_matrix/client/r0/directory/list/room/{room_id}",
        headers={
            "Authorization": f"Bearer {config.user_token}",
        },
    ) as response:
        if response.status == 429:
            await asyncio.sleep(1)
            return await get_room_directory_status(config, session, room_id)
        try:
            response.raise_for_status()
            data = await response.json()
            logger.debug("Got room directory visibility: %s, %s", room_id, data)
            return data.get("visibility")
        except Exception as ex:
            logger.warning("Failed to get room directory visibility for room %s: %s", room_id, ex)
            return


async def recreate_room(
    room: MatrixRoom, client: AsyncClient, config: Config, store: Storage, last_event_id: str,
) -> Optional[str]:
    """
    Replace a room with a new room.
    """
    try:
        alias = None
        alt_aliases = []
        # Remove aliases from the old room
        aliases = await client.room_get_state_event(room.room_id, "m.room.canonical_alias")
        if isinstance(aliases, RoomGetStateEventResponse):
            alias = aliases.content.get("alias")
            alt_aliases = aliases.content.get("alt_aliases", [])

        if alias or alt_aliases:
            logger.info(f"Removing canonical alias {alias} and {len(alt_aliases)} alt aliases from old room")
            if alias:
                await client.room_delete_alias(room_alias=alias)
            await client.room_put_state(
                room_id=room.room_id,
                event_type="m.room.canonical_alias",
                content={
                    "alias": None,
                    "alt_aliases": [],
                },
            )

        # Get room visibility
        room_visibility = await with_ratelimit(client, "room_get_visibility", room_id=room.room_id)
        logger.debug(f"Room visibility is: {room_visibility}")

        # Calculate users
        users = {user.user_id for user in room.users.values() if user.user_id != config.user_id}
        invited_users = {user.user_id for user in room.invited_users.values() if user.user_id != config.user_id}
        users = users.union(invited_users)

        # Power levels
        power_levels, _users = await get_room_power_levels(client, room.room_id)
        # Ensure we don't immediately demote ourselves
        power_levels.content["users"][config.user_id] = 100
        # Add secondary admin if configured
        if config.rooms.get("secondary_admin"):
            users.add(config.rooms.get("secondary_admin"))
            power_levels.content["users"][config.rooms.get("secondary_admin")] = 100

        # Create new room
        local_users = [user for user in users if user.endswith(f":{config.server_name}") and user != config.user_id]
        remote_users = [user for user in users if not user.endswith(f":{config.server_name}")
                        and user != config.user_id]
        initial_state = []
        if room.encrypted:
            initial_state.append({
                "type": "m.room.encryption",
                "state_key": "",
                "content": {
                    "algorithm": "m.megolm.v1.aes-sha2",
                    "rotation_period_ms": 604800000,
                    "rotation_period_msgs": 100,
                },
            })

        logger.info(f"Recreating room {room.room_id} for {len(users)} users")
        federated = True if config.rooms.get("recreate_as_federated", False) else room.federate
        new_room = await client.room_create(
            visibility=RoomVisibility(room_visibility.visibility),
            name=room.name,
            topic=room.topic,
            federate=federated,
            initial_state=initial_state,
            power_level_override=power_levels.content,
            predecessor={
                "event_id": last_event_id,
                "room_id": room.room_id,
            },
        )
        if isinstance(new_room, RoomCreateError):
            logger.warning(f"Failed to create new room: {new_room.status_code} / {new_room.message}")
            return

        logger.info(f"New room id for {room.room_id} is {new_room.room_id}")

        # Rename the old room
        await client.room_put_state(
            room_id=room.room_id,
            event_type="m.room.name",
            content={
                "name": f"{config.rooms.get('recreate_old_room_name_prefix', 'OLD')} {room.name}",
            },
        )

        # Move room avatar
        avatar_state = await client.room_get_state_event(room.room_id, "m.room.avatar")
        if isinstance(avatar_state, RoomGetStateEventResponse):
            await client.room_put_state(
                room_id=new_room.room_id,
                event_type="m.room.avatar",
                content=avatar_state.content,
            )
            await client.room_put_state(
                room_id=room.room_id,
                event_type="m.room.avatar",
                content={
                    "url": None,
                },
            )

        # If maintained by Bubo, update the database
        if alias and alias.endswith(f":{config.server_name}"):
            maintained_room_id = store.get_room_id(alias)
            if maintained_room_id:
                store.set_room_id(alias, new_room.room_id)

        # Various things if Synapse admin for local users
        if config.is_synapse_admin:
            # Try to force join local users
            if local_users:
                try:
                    joined_count = await synapse_admin.join_users(config, local_users, new_room.room_id)
                    logger.debug(f"Successfully joined {joined_count} local users to new room {new_room.room_id}")
                except Exception as ex:
                    logger.warning(
                        f"Failed to join any local users to new room {new_room.room_id} via Synapse admin: {ex}",
                    )

            # Get temporary access tokens for the users
            user_tokens = await synapse_admin.get_temporary_user_tokens(config, local_users)
            async with aiohttp.ClientSession() as session:
                for user, token in user_tokens.items():
                    logger.debug("Room tag tokens: %s, %s", user, token)
                    # Copy over room tags
                    tags = await get_user_room_tags(config, session, user, room.room_id, token)
                    logger.debug("Got tags: %s", tags)
                    if tags:
                        # Copy to the new room
                        await set_user_room_tags(config, session, user, new_room.room_id, token, tags)
                        # Remove favourite from old room
                        if "m.favourite" in tags.keys():
                            await delete_user_room_tag(config, session, user, room.room_id, token, "m.favourite")
                    # Mark old room as low priority, if not already
                    if not tags or "m.lowpriority" not in tags.keys():
                        await set_user_room_tag(config, session, user, room.room_id, token, "m.lowpriority", 0)

        # Invites, all if not synapse admin, remote if locals were joined already
        invite_users = remote_users
        if not config.is_synapse_admin:
            invite_users = invite_users + remote_users

        for user in invite_users:
            response = await client.room_invite(new_room.room_id, user)
            if isinstance(response, RoomInviteError):
                logger.warning(f"Failed to invite user {user} to new room {new_room.room_id}: "
                               f"{response.message} / {response.status_code}")

        # Add aliases to the new room
        if alias or alt_aliases:
            if alias:
                await client.room_put_alias(
                    room_alias=alias,
                    room_id=new_room.room_id,
                )
            await client.room_put_state(
                room_id=new_room.room_id,
                event_type="m.room.canonical_alias",
                content={
                    "alias": alias,
                    "alt_aliases": alt_aliases,
                },
            )

        # Room directory
        async with aiohttp.ClientSession() as session:
            directory_visibility = await get_room_directory_status(config, session, room.room_id)
            if directory_visibility == "public":
                await set_room_directory_status(config, session, room.room_id, "private")
                await set_room_directory_status(config, session, new_room.room_id, "public")

        # Post a message to the start of the timeline of the new room and the end of the timeline for the
        # old room
        old_room_link = f"https://matrix.to/#/{room.room_id}?via={config.server_name}"
        new_room_link = f"https://matrix.to/#/{new_room.room_id}?via={config.server_name}"
        await send_text_to_room(
            client,
            room.room_id,
            f"#### This room has been replaced\n\nTo continue discussion in the new room, click this "
            f"link: {new_room_link}",
        )
        # Unfortunately we can't use matrix-nio here as it doesn't know about the room and will die with
        # LocalProtocolError as it fails to find the room in its local cache. Use the C2S API directly.
        await send_text_to_room_c2s(
            config,
            new_room.room_id,
            f"#### This room replaces the old '{room.name}' room {room.room_id}.\n\nShould you need to view "
            f"the old room, click this link: {old_room_link}",
        )

        return new_room.room_id
    except Exception as ex:
        import traceback
        logger.error(f"Failed to recreate room {room.room_id}: {ex}")
        logger.error(traceback.format_exc())
        try:
            await send_text_to_room(
                client,
                room.room_id,
                f"Failed to recreate room. Please look at logs or contact support.",
            )
        except Exception as ex:
            logger.error(f"Failed to inform of error to the room to be recreated: {ex}")


async def set_room_directory_status(
    config: Config, session: aiohttp.ClientSession, room_id: str, visibility: str,
) -> bool:
    async with session.put(
        f"{config.homeserver_url}/_matrix/client/r0/directory/list/room/{room_id}",
        json={
            "visibility": visibility,
        },
        headers={
            "Authorization": f"Bearer {config.user_token}",
        },
    ) as response:
        if response.status == 429:
            await asyncio.sleep(1)
            return await set_room_directory_status(config, session, room_id, visibility)
        try:
            response.raise_for_status()
            logger.debug("Room directory visibility has been set: %s, %s", room_id, visibility)
            return True
        except Exception as ex:
            logger.warning("Failed to set room directory visibility for room %s: %s", room_id, ex)
            return False


async def set_user_power(
    room_id: str, user_id: str, client: AsyncClient, power: int,
) -> Union[int, RoomGetStateEventError, RoomGetStateEventResponse, RoomPutStateError, RoomPutStateResponse]:
    """
    Set user power in a room.
    """
    logger.debug(f"Setting user power: {room_id}, user: {user_id}, level: {power}")
    state_response = await client.room_get_state_event(room_id, "m.room.power_levels")
    if isinstance(state_response, RoomGetStateEventError):
        logger.error(f"Failed to fetch room {room_id} state: {state_response.message}")
        return state_response
    if isinstance(state_response.transport_response, TransportResponse):
        status_code = state_response.transport_response.status_code
    elif isinstance(state_response.transport_response, ClientResponse):
        status_code = state_response.transport_response.status
    else:
        logger.error(f"Failed to determine status code from state response: {state_response}")
        return state_response
    if status_code >= 400:
        logger.warning(
            f"Failed to set user {user_id} power in {room_id}, response {status_code}"
        )
        return status_code
    state_response.content["users"][user_id] = power
    response = await with_ratelimit(
        client,
        "room_put_state",
        room_id=room_id,
        event_type="m.room.power_levels",
        content=state_response.content,
    )
    logger.debug(f"Power levels update response: {response}")
    return response


async def set_user_room_tag(
    config: Config, session: aiohttp.ClientSession, user: str, room_id: str, token: str, tag: str, order: float,
) -> bool:
    async with session.put(
            f"{config.homeserver_url}/_matrix/client/r0/user/{user}/rooms/{room_id}/tags/{tag}",
            json={
                "order": order,
            },
            headers={
                "Authorization": f"Bearer {token}",
            },
    ) as response:
        if response.status == 429:
            await asyncio.sleep(1)
            return await set_user_room_tag(config, session, user, room_id, token, tag, order)
        try:
            response.raise_for_status()
            logger.debug("Set room tag for user: %s, %s, %s", user, room_id, tag)
            return True
        except Exception as ex:
            logger.warning("Failed to set room tag %s for user %s for room %s: %s", tag, user, room_id, ex)
            return False


async def set_user_room_tags(
    config: Config, session: aiohttp.ClientSession, user: str, room_id: str, token: str, tags: Dict,
) -> None:
    for tag, data in tags.items():
        await set_user_room_tag(config, session, user, room_id, token, tag, data.get("order"))


async def maintain_configured_rooms(client: AsyncClient, store: Storage, config: Config):
    """
    Maintains the list of configured rooms.

    Creates if missing. Corrects if details are not correct.
    """
    logger.info("Starting maintaining of rooms")

    results = store.cursor.execute("""
        select * from rooms
    """)

    rooms = results.fetchall()
    for room in rooms:
        try:
            await ensure_room_exists(room, client, store, config)
        except Exception as e:
            logger.error(f"Error with room '{room[2]}': {e}")
