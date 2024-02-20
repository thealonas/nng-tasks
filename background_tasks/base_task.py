import sentry_sdk
from nng_sdk.logger import get_logger
from nng_sdk.postgres.nng_postgres import NngPostgres


class BaseTask:
    def __init__(self):
        self.logging = get_logger()
        self.postgres = NngPostgres()

    def _run(self):
        pass

    def run(self):
        try:
            self._run()
        except Exception as e:
            sentry_sdk.capture_exception(e)
