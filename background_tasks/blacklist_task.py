from nng_sdk.logger import get_logger
from nng_sdk.pydantic_models.user import User
from nng_sdk.vk.actions import (
    get_all_banned,
    get_all_managers,
    edit_manager,
    unban_users,
    ban_users,
    get_users_data,
)

from background_tasks.base_task import BaseTask


class BlacklistTask(BaseTask):
    logging = get_logger()

    dogs: list[int] = []

    def add_dog(self, dog_id: int):
        self.dogs.append(dog_id)
        self.dogs = list(set(self.dogs))

    def _run(self):
        all_banned: list[User] = self.postgres.users.get_banned_users()
        all_groups: list[int] = [
            i.group_id for i in self.postgres.groups.get_all_groups()
        ]

        self.fetch_dogs([i.user_id for i in all_banned])
        self.logging.info(f"всего {len(self.dogs)} собак")

        for group in all_groups:
            banned = get_all_banned(group)
            actual_banned: list[int] = []

            for item in banned:
                if "profile" not in item:
                    continue
                if "id" not in item["profile"]:
                    continue
                actual_banned.append(int(item["profile"]["id"]))

            self.logging.info(f"группа {group} имеет {len(actual_banned)} забаненных")

            managers: list[int] = [i["id"] for i in get_all_managers(group)]

            self.fire_banned_managers(group, all_banned, managers)
            self.ensure_banned_users_in_group(group, all_banned, actual_banned)
            self.ensure_no_incorrect_bans(group, all_banned, actual_banned)

    def fetch_dogs(self, users: list[int]):
        response = get_users_data(users)
        for user in response:
            if "id" not in user or "deactivated" not in user:
                continue
            self.add_dog(user["id"])

    def fire_banned_managers(
        self, group: int, banned_users: list[User], managers: list[int]
    ):
        bnnd = [i for i in banned_users if i.user_id in managers]
        for user in bnnd:
            self.logging.info(f"убираю менеджера {user.user_id} в группе {group}")
            edit_manager(group, user.user_id, None)
            user.groups = []
            self.postgres.users.update_user(user)

    def ensure_banned_users_in_group(
        self, group: int, all_banned: list[User], actual_banned: list[int]
    ):
        not_bnnd = [
            i
            for i in all_banned
            if i.user_id not in actual_banned and i.user_id not in self.dogs
        ]

        if len(not_bnnd) <= 0:
            self.logging.info("нет юзеров на блокировку")
            return

        self.logging.info(
            f"добавляю {len(not_bnnd)} ({', '.join(map(str, [i.user_id for i in not_bnnd]))}) "
            f"юзеров в чс в группе {group}"
        )

        ban_users(group=group, users=[user.user_id for user in not_bnnd])

    def ensure_no_incorrect_bans(
        self, group, all_banned: list[User], actual_banned: list[int]
    ):
        all_banned_ids = [i.user_id for i in all_banned]
        should_not_be_banned = [i for i in actual_banned if i not in all_banned_ids]

        if len(should_not_be_banned) <= 0:
            self.logging.info("нет юзеров на разблокировку")
            return

        self.logging.info(
            f"удаляю {len(should_not_be_banned)} ({', '.join(map(str, should_not_be_banned))}) юзеров из чс в группе {group}"
        )
        unban_users(group=group, users=should_not_be_banned)
