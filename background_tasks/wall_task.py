import time

import nng_sdk.one_password.models.algolia_credentials
from nng_sdk.pydantic_models.group import Group
from nng_sdk.vk.actions import get_last_post, get_wall_posts, delete_posts, repost
from vk_api import ApiError

from background_tasks.base_task import BaseTask


class WallTask(BaseTask):
    main_group_id = 147811741
    last_post = 0

    def _run(self):
        old_captcha_handler = nng_sdk.vk.actions.captcha_handler
        nng_sdk.vk.actions.captcha_handler = lambda: time.sleep(60 * 60)

        try:
            self.last_post = get_last_post(self.main_group_id)["id"]

            self.logging.info(f"последний пост в главном сообществе: {self.last_post}")

            groups: list[Group] = self.postgres.groups.get_all_groups()

            self.logging.info(f"всего групп: {len(groups)}")

            for group in groups:
                if not self.need_update(group.group_id):
                    self.logging.info(
                        f"обработка группы @{group.screen_name} не требуется"
                    )
                    continue

                self.logging.info(f"обрабатываю группу @{group.screen_name}")
                self.reset_group_wall(group.group_id)
        finally:
            nng_sdk.vk.actions.captcha_handler = old_captcha_handler

    def reset_group_wall(self, group: int):
        posts = [int(i["id"]) for i in get_wall_posts(group)]
        delete_posts(group, posts)

        if len(posts) != 0:
            self.logging.info(f"{len(posts)} постов удалено")

        wall_object = f"wall-{self.main_group_id}_{self.last_post}"

        repost(wall_object, group)
        self.logging.info(f"запись {wall_object} репостнута")

    def need_update(self, group: int) -> bool:
        last_group_post: dict
        try:
            all_posts = get_wall_posts(group)
            last_group_post = all_posts[0]
        except IndexError:
            return True
        except ApiError:
            return False

        if len(all_posts) != 1:
            return True

        if "copy_history" not in last_group_post:
            return True

        copy_history = last_group_post["copy_history"]
        for post in copy_history:
            if post["id"] == self.last_post:
                return False

        return True
