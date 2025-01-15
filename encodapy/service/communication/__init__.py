"""
This package contains modules for handling different types of connections
for the TWE-Flex project. It includes connections for FIWARE and file-based
communication.

Modules:
    fiware_connection: Contains the FiwareConnection class for handling FIWARE communication.
    file_connection: Contains the FileConnection class for handling file-based communication.
"""

from .fiware_connection import FiwareConnection
from .file_connection import FileConnection
from .mqtt_connection import MqttConnection
