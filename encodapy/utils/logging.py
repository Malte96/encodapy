"""
Description: LoggerControl class to control the log level of the application.
Authors: Martin Altenburger
"""

import os
import sys
from loguru import logger
from encodapy.config.default_values import DefaultEnvVariables

class LoggerControl:
    """
        LoggerControl class for the control of the log level of the application.
    """

    def __init__(self) -> None:

        log_level = os.environ.get(
            "LOG_LEVEL", DefaultEnvVariables.LOG_LEVEL.value
        ).upper()

        logger.remove()
        logger.add(sys.stdout, level=log_level)
