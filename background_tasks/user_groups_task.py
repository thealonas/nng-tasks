import datetime

from nng_sdk.pydantic_models.user import User, TrustInfo
from nng_sdk.vk.actions import get_all_managers, get_users_data

from background_tasks.base_task import BaseTask


class UserGroupsTask(BaseTask):
    users: dict[int, list[int]] = {}

    def add_group(self, group_id: int, managers: list[int]):
        for user in managers:
            self.users.setdefault(user, []).append(group_id)

    def _run(self):
        # берем все группы
        all_groups: list[int] = [
            i.group_id for i in self.postgres.groups.get_all_groups()
        ]

        # получаем в них всех редакторов и кэшируем в self.users
        for group in all_groups:
            all_managers: list[dict] = get_all_managers(group)
            self.add_group(group, [i["id"] for i in all_managers])

        # получаем всех юзеров
        all_users = self.postgres.users.get_all_users()

        # смотрим, есть ли редакторы которых нет в бд
        users_not_in_db = [
            user
            for user in self.users.keys()
            if user not in [i.user_id for i in all_users]
        ]

        # если такие есть
        if users_not_in_db:
            # получаем их имена из вк
            users_data = get_users_data(users_not_in_db)

            # приводим в удобный вид
            vk_data = {
                user["id"]: f"{user['first_name']} {user['last_name']}"
                for user in users_data
            }

            for user, name in vk_data.items():
                # создаем профиль
                self.postgres.users.add_user(
                    User(
                        user_id=user,
                        name=name,
                        admin=False,
                        trust_info=TrustInfo.create_default(),
                        join_date=datetime.date.today(),
                        groups=[],
                        violations=[],
                    )
                )

        # проходимся по всем юзерам в бд
        for user in all_users:
            # если юзер есть в кэше - устанавливаем ему группы из кэша
            if user.user_id in self.users.keys():
                user.groups = self.users[user.user_id]
            # иначе просто удаляем запись о группах
            else:
                user.groups = []
            self.postgres.users.update_user(user)
