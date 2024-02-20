import asyncio
import time

import nng_sdk.vk.actions
import sentry_sdk
from nng_sdk.vk.vk_manager import VkManager

from background_tasks.base_task import BaseTask
from background_tasks.blacklist_task import BlacklistTask
from background_tasks.inactive_revoke_task import InactiveRevokeTask
from background_tasks.status_task import StatusTask
from background_tasks.user_groups_task import UserGroupsTask
from background_tasks.wall_task import WallTask
from task_scheduler import TaskScheduler

sentry_sdk.init(
    dsn="https://8f023142ec813e1f715dc74d5c5a7cb7@o555933.ingest.sentry.io/4505869441630208",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

if __name__ == "__main__":
    VkManager().auth_in_vk()
    VkManager().auth_in_bot()

    nng_sdk.vk.actions.rate_limit_handler = lambda: time.sleep(60 * 60)
    nng_sdk.vk.actions.captcha_handler = lambda: time.sleep(10)

    wall_task: BaseTask = WallTask()
    status_task: BaseTask = StatusTask()
    inactive_revoke_task: BaseTask = InactiveRevokeTask()
    blacklist_task: BaseTask = BlacklistTask()
    user_groups_task: BaseTask = UserGroupsTask()

    scheduler = TaskScheduler()

    scheduler.add_by_time_task("wall_task", "13:00", wall_task.run)
    scheduler.add_by_time_task("status_task", "00:00", status_task.run)
    scheduler.add_interval_task("user_groups_task", 7, user_groups_task.run)
    scheduler.add_interval_task("inactive_revoke_task", 14, inactive_revoke_task.run)
    scheduler.add_interval_task("blacklist_task", 14, blacklist_task.run)

    while True:
        asyncio.run(scheduler.run())
