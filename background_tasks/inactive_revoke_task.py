import datetime

from nng_sdk.logger import get_logger
from nng_sdk.pydantic_models.user import User
from nng_sdk.vk.actions import edit_manager, get_users_data

from background_tasks.base_task import BaseTask


class InactiveRevokeTask(BaseTask):
    logging = get_logger()

    inactive_users: list[User] = []

    def add_inactive(self, user: User):
        if any([i.user_id for i in self.inactive_users if i.user_id == user.user_id]):
            return

        self.inactive_users.append(user)

    def fetch_inactive_users(self, users: list[User]):
        users_data: list[dict] = get_users_data([i.user_id for i in users])
        for user in users_data:
            user_id: int = user.get("id")
            if not user_id:
                continue

            target_users = [i for i in users if i.user_id == user_id]
            if not any(target_users):
                continue

            target_user: User = target_users[0]

            if user.get("deactivated"):
                self.add_inactive(target_user)
                continue

            last_seen = user.get("last_seen")
            if not last_seen or not last_seen["time"]:
                continue

            last_seen_datetime = datetime.datetime.fromtimestamp(last_seen["time"])
            if not self.was_online_within_six_months(last_seen_datetime):
                self.add_inactive(target_user)
                continue

    @staticmethod
    def was_online_within_six_months(last_seen: datetime.datetime):
        now = datetime.datetime.now()
        if last_seen > now:
            return True

        return (now - last_seen).days <= 180

    def revoke_user(self, user: User):
        for group in user.groups:
            edit_manager(group, user.user_id, None)
        user.groups = []
        self.postgres.users.update_user(user)

    def _run(self):
        users: list[User] = [i for i in self.postgres.users.get_all_editors()]
        self.logging.info(f"всего {len(users)} редакторов")

        self.fetch_inactive_users(users)
        self.logging.info(f"всего неактивных редакторов: {len(self.inactive_users)}")

        for user in self.inactive_users:
            self.logging.info(f"снимаю все группы у {user.user_id}")
            self.revoke_user(user)
