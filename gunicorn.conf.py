import logging

import cdislogging
import gunicorn.glogging

import gen3discoveryai.config


class CDISLogger(gunicorn.glogging.Logger):
    """
    Initialize root and gunicorn loggers with cdislogging configuration.
    """

    @staticmethod
    def _remove_handlers(logger):
        """
        Use Python's built-in logging module to remove all handlers associated
        with logger (logging.Logger).
        """
        while logger.handlers:
            logger.removeHandler(logger.handlers[0])

    def __init__(self, cfg):
        """
        Apply cdislogging configuration after gunicorn has set up it's loggers.
        """
        super().__init__(cfg)

        self._remove_handlers(logging.getLogger())
        cdislogging.get_logger(
            None, log_level="debug" if gen3discoveryai.config.DEBUG else "warn"
        )
        for logger_name in ["gunicorn", "gunicorn.error", "gunicorn.access"]:
            self._remove_handlers(logging.getLogger(logger_name))
            cdislogging.get_logger(
                logger_name,
                log_level="debug" if gen3discoveryai.config.DEBUG else "info",
            )


logger_class = CDISLogger

wsgi_app = "gen3discoveryai.main:app"
bind = "0.0.0.0:8089"
workers = 1
user = "gen3"
group = "gen3"

# OpenAI API can take a while
# default was `30`
timeout = 300
graceful_timeout = 300
