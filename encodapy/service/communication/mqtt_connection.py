"""
Description: This file contains the class MqttConnection, 
which is used to store the connection parameters for the MQTT broker.
Author: Maximilian Beyer
"""

import os
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from encodapy.utils.error_handling import NotSupportedError, ConfigError
from encodapy.config import DefaultEnvVariables

class MqttConnection:
    """
    Class for the connection to a mqtt broker.
    Only a helper class.
    """

    def __init__(self):
        self.mqtt_params = {}
        self.load_mqtt_params()
        self.prepare_mqtt_connection()

    def load_mqtt_params(self):
        """
        Function to load the mqtt parameters
        """
        self.mqtt_params["broker"] = os.environ.get("MQTT_BROKER", DefaultEnvVariables.MQTT_BROKER.value)
        self.mqtt_params["port"] = int(os.environ.get("MQTT_PORT", DefaultEnvVariables.MQTT_PORT.value))
        self.mqtt_params["username"] = os.environ.get("MQTT_USERNAME", DefaultEnvVariables.MQTT_USERNAME.value)
        self.mqtt_params["password"] = os.environ.get("MQTT_PASSWORD", DefaultEnvVariables.MQTT_PASSWORD.value)
        self.mqtt_params["topic"] = os.environ.get("MQTT_TOPIC_PREFIX", DefaultEnvVariables.MQTT_TOPIC_PREFIX.value)

        if not self.mqtt_params["broker"] or not self.mqtt_params["port"]:
            raise ConfigError("MQTT broker and port must be set")

    def prepare_mqtt_connection(self):
        """
        Function to prepare the mqtt connection
        """
        self.client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(self.mqtt_params["username"], self.mqtt_params["password"])
        self.client.connect(self.mqtt_params["broker"], self.mqtt_params["port"])

    def publish(self, topic, payload):
        """
        Function to publish a message to a topic
        """
        if not self.client:
            raise NotSupportedError("MQTT client is not connected")
        self.client.publish(topic, payload)

    def subscribe(self, topic):
        """
        Function to subscribe to a topic
        """
        if not self.client:
            raise NotSupportedError("MQTT client is not connected")
        self.client.subscribe(topic)

    def on_message(self, client, userdata, message):
        """
        Callback function for received messages
        """
        print(f"Received message: {message.payload.decode()} on topic {message.topic}")

    def start(self):
        """
        Function to start the mqtt client loop
        """
        self.client.on_message = self.on_message
        self.client.loop_start()

    def stop(self):
        """
        Function to stop the mqtt client loop
        """
        self.client.loop_stop()
        self.client.disconnect()
