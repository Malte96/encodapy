# Description: LoggerControl class to control the log level of the application.
# Authors: Martin Altenburger

import sys
import os
from loguru import logger
from controller_software.config.default_values import DefaultEnvVariables

class LoggerControl():

    def __init__(self) -> None:

        log_level = os.environ.get("LOG_LEVEL", DefaultEnvVariables.LOG_LEVEL.value).upper()

        logger.remove()
        logger.add(sys.stdout, level=log_level)