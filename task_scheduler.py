import asyncio
import datetime
import logging
from typing import Callable

import sentry_sdk
from nng_sdk.postgres.exceptions import ItemNotFoundException
from nng_sdk.pydantic_models.startup import Startup

from background_tasks.base_task import BaseTask


class TaskScheduler(BaseTask):
    def __init__(self):
        super().__init__()
        self.by_time_tasks = []
        self.interval_tasks = []

    def add_by_time_task(
        self, task_name: str, execution_time: str, task_func: Callable
    ):
        self.by_time_tasks.append(
            (task_name, datetime.datetime.strptime(execution_time, "%H:%M"), task_func)
        )

    def add_interval_task(
        self,
        task_name: str,
        interval_days: int,
        task_func: Callable,
        run_at_startup: bool = True,
    ):
        self.interval_tasks.append(
            (task_name, interval_days, task_func, run_at_startup)
        )

    def get_startup_or_none(self, task_name: str) -> datetime.datetime | None:
        try:
            return self.postgres.startup.get_startup_for_service(task_name).time_log
        except ItemNotFoundException:
            return None

    async def run(self):
        tasks_and_target_datetime = {}
        tasks_and_callables = {}
        tasks_and_should_log = {}

        now = datetime.datetime.now()

        for task_name, execution_time, task_func in self.by_time_tasks:
            next_execution_time = datetime.datetime(
                now.year, now.month, now.day, execution_time.hour, execution_time.minute
            )

            delta = next_execution_time - now

            if delta <= datetime.timedelta(0):
                tasks_and_target_datetime[task_name] = (
                    next_execution_time + datetime.timedelta(days=1)
                )
            else:
                tasks_and_target_datetime[task_name] = datetime.datetime(
                    now.year,
                    now.month,
                    now.day,
                    execution_time.hour,
                    execution_time.minute,
                )

            tasks_and_callables[task_name] = task_func
            tasks_and_should_log[task_name] = False

        for index, (task_name, interval_days, task_func, run_at_startup) in enumerate(
            self.interval_tasks
        ):
            time_log: datetime.datetime | None = self.get_startup_or_none(task_name)
            if time_log:
                target_datetime = time_log + datetime.timedelta(days=interval_days)
                if target_datetime < now:
                    target_datetime = now + datetime.timedelta(days=interval_days)
                tasks_and_target_datetime[task_name] = target_datetime
            elif run_at_startup:
                tasks_and_target_datetime[task_name] = now
            else:
                tasks_and_target_datetime[task_name] = now + datetime.timedelta(
                    days=interval_days
                )

            tasks_and_callables[task_name] = task_func
            tasks_and_should_log[task_name] = True
            self.interval_tasks[index] = (task_name, interval_days, task_func, False)

        tasks_and_target_datetime = dict(
            sorted(tasks_and_target_datetime.items(), key=lambda item: item[1])
        )

        for task_name, target_datetime in tasks_and_target_datetime.items():
            delta_time = target_datetime - datetime.datetime.now()

            if delta_time.total_seconds() <= 0:
                logging.info(f"запускаю задачу {task_name}")
            else:
                logging.info(
                    f"следующая задача {task_name} запустится {target_datetime.strftime('%d.%m.%Y %H:%M')}"
                )
                await asyncio.sleep(
                    (target_datetime - datetime.datetime.now()).total_seconds()
                )

            try:
                self._run_task(
                    task_name,
                    tasks_and_callables[task_name],
                    tasks_and_should_log[task_name],
                )
            except Exception as e:
                sentry_sdk.capture_exception(e)
                logging.exception(e)

    def save_progress(self, task_name: str):
        self.postgres.startup.upload_startup(
            Startup(service_name=task_name, time_log=datetime.datetime.now())
        )

    def _run_task(self, task_name: str, task_func: Callable, log: bool):
        try:
            task_func()
            self.logging.info(f"задача {task_name} завершена")
        except Exception as e:
            sentry_sdk.capture_exception(e)
            self.logging.exception(e)
            self.logging.warn(f"задача {task_name} завершена с ошибками")
        if log:
            self.save_progress(task_name)
            self.logging.info("прогресс записан в бд")
