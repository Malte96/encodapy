# Description: Enum classes for the types in the configuration
# Authors: Martin Altenburger

# TODO: Add the needed types
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
    """Enum class for the controller components"""
    # TODO: Which components are needed?
    
    STORAGE = "storage"
    HYGIENICCONTROLLER = "hygienic_controller"