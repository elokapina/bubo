import asyncio
import dataclasses
import logging
from typing import Dict

import aiohttp
# noinspection PyPackageRequirements
from nio import AsyncClient

from bubo.config import Config, load_config
from bubo.rooms import ensure_room_exists
from bubo.storage import Storage

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class DiscourseClient:
    api_key: str
    api_username: str
    url: str

    async def do_request(self, method, path, data: Dict = None):
        logger.debug("Making %s request to %s%s", method, self.url, path)
        async with aiohttp.ClientSession() as session:
            async with getattr(session, method.lower())(
                    f"{self.url}{path}",
                    json=data,
                    headers=self.request_headers,
            ) as response:
                if response.status == 429:
                    await asyncio.sleep(3)
                    return await self.do_request(method, path, data)
                response.raise_for_status()
                return await response.json()

    @property
    def request_headers(self) -> Dict:
        return {
            "Api-Key": self.api_key,
            "Api-Username": self.api_username,
            "Content-Type": "application/json",
        }


@dataclasses.dataclass
class DiscourseGroup:
    id: int
    name: str
    user_count: int
    allow_membership_requests: bool = None
    automatic: bool = None
    bio_cooked: str = None
    bio_excerpt: str = None
    bio_raw: str = None
    can_admin_group: bool = None
    can_see_members: bool = None
    default_notification_level: int = None
    display_name: str = None
    flair_bg_color: str = None
    flair_color: str = None
    flair_url: str = None
    full_name: str = None
    grant_trust_level: str = None
    has_messages: bool = None
    incoming_email: str = None
    is_group_owner: bool = None
    is_group_user: bool = None
    members_visibility_level: int = None
    membership_request_template: str = None
    mentionable_level: int = None
    messageable_level: int = None
    primary_group: bool = None
    public_admission: bool = None
    public_exit: bool = None
    publish_read_state: bool = None
    title: str = None
    visibility_level: int = None

    @property
    def short_name(self):
        """
        Return the name with leading prefix stripped.

        This assumes group name is in format `prefix-actualname`.
        """
        if not self.name.find("-") > -1:
            return self.name
        return self.name.split("-", 1)[1]


class Discourse:
    client: DiscourseClient
    config: Config
    groups: Dict[str, DiscourseGroup]

    def __init__(self):
        self.config = load_config()
        self.client = DiscourseClient(
            url=self.config.discourse.get("url"),
            api_username=self.config.discourse.get("api_username"),
            api_key=self.config.discourse.get("api_key"),
        )

    async def get_groups(self) -> Dict[str, DiscourseGroup]:
        """
        Get list of groups from Discourse.
        """
        self.groups = {}
        path = "/groups.json"
        while True:
            response = await self.client.do_request("GET", path)
            for group in response.get("groups", []):
                self.groups[group.get("name")] = DiscourseGroup(**group)
            if response.get("total_rows_groups") > len(self.groups.values()):
                path = f'/groups.json?{response.get("load_more_groups").split("?")[1]}'
            else:
                break
        logger.info("Found a total of %s groups from Discourse", len(self.groups.keys()))
        return self.groups

    async def sync_groups_as_spaces(self, client: AsyncClient, store: Storage):
        """
        Sync groups from Discourse as Matrix spaces.

        # TODO create a separate temporary client
        # is store safe to recreate given it's sqlite?
        # possibly only recreate them if not passed in
        """
        # TODO ensure parent spaces exist

        groups = await self.get_groups()
        for name, group in groups.items():
            logger.info("Ensuring Discourse group %s has a space", name)
            room_params = (
                None,
                group.full_name or group.title or group.short_name,
                group.name,
                None,
                group.title,
                None,
                False,
                False,
                "space",
            )
            try:
                await ensure_room_exists(room_params, client, store, self.config)
            except Exception as ex:
                logger.warning("Failed to ensure group %s exists as a space: %s", name, ex)

            # TODO add space to parent spaces
            # TODO ensure space rooms
