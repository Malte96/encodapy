"""
Description: This file contains the class FiwareConnections, 
which is used to store the connection parameters for the Fiware and CrateDB connections.
Author: Paul Seidel
"""

from encodapy.utils.error_handling import NotSupportedError


class MqttConnection:
    """
    Class for the connection to a mqtt broker.
    Only a helper class.
    #TODO: Implement the connection to the mqtt broker
    """

    def __init__(self):
        self.mqtt_params = {}

    def load_mqtt_params(self):
        """
        Function to load the mqtt parameters
        """
        raise NotSupportedError("MQTT interface not implemented yet.")
