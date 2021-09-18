from typing import Union

from synapse.module_api import ModuleApi


class DenyEventsModule:
    def __init__(self, config: dict, api: ModuleApi):
        self.config = config
        self.api = api

        self.api.register_spam_checker_callbacks(
            check_event_for_spam=self.check_event_for_spam,
            user_may_invite=self.user_may_invite,
        )

    @staticmethod
    def parse_config(config):
        return config

    async def check_event_for_spam(self, event: "synapse.events.EventBase") -> Union[bool, str]:
        if event.room_id in self.config.get("rooms"):
            return "This room does not accept events."
        return False

    async def user_may_invite(self, inviter: str, invitee: str, room_id: str) -> bool:
        if room_id in self.config.get("rooms"):
            return False
        return True

