from nng_sdk.logger import get_logger
from nng_sdk.vk.actions import (
    get_groups_statuses,
    set_statuses,
)

from background_tasks.base_task import BaseTask


class StatusTask(BaseTask):
    logging = get_logger()

    def _run(self):
        groups = [group.group_id for group in self.postgres.groups.get_all_groups()]

        self.logging.info(f"всего групп: {len(groups)}")

        statuses = get_groups_statuses(groups)
        groups_with_status = [
            group_id for group_id in statuses if statuses[group_id] != ""
        ]

        if len(groups_with_status) > 0:
            self.logging.info(
                f"количество групп со статусом: {len(groups_with_status)}: {', '.join(map(str, groups_with_status))}, начинаю уборку"
            )
            set_statuses(groups_with_status, "")
        else:
            self.logging.info("нет групп со статусом")
