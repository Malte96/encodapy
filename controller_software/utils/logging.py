"""
Description: LoggerControl class to control the log level of the application.
Authors: Martin Altenburger
"""

import os
import sys

from controller_software.config.default_values import DefaultEnvVariables
from loguru import logger


class LoggerControl:

    def __init__(self) -> None:

        log_level = os.environ.get("LOG_LEVEL", DefaultEnvVariables.LOG_LEVEL.value).upper()

        logger.remove()
        logger.add(sys.stdout, level=log_level)
