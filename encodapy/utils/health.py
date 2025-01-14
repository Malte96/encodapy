"""
Description: This module is used to update the health file for the health check.\
    The health file is checked by the healthcheck.
Author: Martin Altenburger
"""

from datetime import datetime, timedelta
from typing import Union
from loguru import logger


async def update_health_file(
    time_cycle: int, timestamp_health: Union[datetime, None], timestamp_now: datetime
):
    """
    create a file that is checked by healthcheck

    Args:
        - time_cycle: int, time in minutes for the health check
        - timestamp_health: datetime, timestamp of the last health check or None,\
            if no health check was done
        - timestamp_now: datetime, current timestamp
    """
    if timestamp_health is None:
        timestamp_health = timestamp_now
        with open("health", "w", encoding="utf-8") as f:
            f.write("OK")
    elif timestamp_health >= (timestamp_now - timedelta(minutes=time_cycle)):
        with open("health", "w", encoding="utf-8") as f:
            f.write("OK")
    else:
        logger.debug("Health-Status not ok - skip writing health file")
        return

    return
