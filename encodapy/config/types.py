"""
Description: Enum classes for the types in the configuration
Authors: Martin Altenburger
"""

from enum import Enum


class Interfaces(Enum):
    """Enum class for the interfaces"""

    MQTT = "mqtt"
    FIWARE = "fiware"
    FILE = "file"


class AttributeTypes(Enum):
    """Enum class for the attribute types"""

    # TODO: Which types are needed?

    TIMESERIES = "timeseries"
    VALUE = "value"


class TimerangeTypes(Enum):
    """Enum class for the timedelta types

    Contains:
    - ABSOLUTE: The timedelta is calculated from the actual time
    - RELATIVE: The timedelta is calculated from the last timestamp
    """

    ABSOLUTE = "absolute"
    RELATIVE = "relative"


class ControllerComponents(Enum):
    """
    Enum class for the controller components, could be extended by the needed components
    """

    # TODO: Which components are needed?

    STORAGE = "storage_controller"
    ENERGYTRENDBAND = "energytrendband_controller"
    HYGIENICCONTROLLER = "hygienic_controller"
    SCHEDULE = "schedule_controller"


class DataQueryTypes(Enum):
    """Enum class for the data query types"""

    CALCULATION = "calculation"
    CALIBRATION = "calibration"


class FileExtensionTypes(Enum):
    """Enum class for file Extensions"""

    CSV = ".csv"
    JSON = ".json"
