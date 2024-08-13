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
    COMMAND = "command"
    
    
class ControllerComponents(Enum):
    """Enum class for the controller components"""
    # TODO: Which components are needed?
    
    STORAGE = "storage"