"""
Description: This file contains the class MqttConnection,
which is used to store the connection parameters for the MQTT broker.
Author: Maximilian Beyer
"""

import os
from datetime import datetime
from typing import Union

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from encodapy.config import DefaultEnvVariables, OutputModel, InputModel, DataQueryTypes
from encodapy.utils.error_handling import ConfigError, NotSupportedError
from encodapy.utils.models import OutputDataEntityModel, InputDataEntityModel


class MqttConnection:
    """
    Class for the connection to a mqtt broker.
    Only a helper class.
    """

    def __init__(self):
        self.mqtt_params = {}

    def load_mqtt_params(self):
        """
        Function to load the mqtt parameters
        """
        self.mqtt_params["broker"] = os.environ.get(
            "MQTT_BROKER", DefaultEnvVariables.MQTT_BROKER.value
        )
        self.mqtt_params["port"] = int(
            os.environ.get("MQTT_PORT", DefaultEnvVariables.MQTT_PORT.value)
        )
        self.mqtt_params["username"] = os.environ.get(
            "MQTT_USERNAME", DefaultEnvVariables.MQTT_USERNAME.value
        )
        self.mqtt_params["password"] = os.environ.get(
            "MQTT_PASSWORD", DefaultEnvVariables.MQTT_PASSWORD.value
        )
        self.mqtt_params["topic"] = os.environ.get(
            "MQTT_TOPIC_PREFIX", DefaultEnvVariables.MQTT_TOPIC_PREFIX.value
        )

        if not self.mqtt_params["broker"] or not self.mqtt_params["port"]:
            raise ConfigError("MQTT broker and port must be set")

    def prepare_mqtt_connection(self):
        """
        Function to prepare the mqtt connection
        """
        self.client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(
            self.mqtt_params["username"], self.mqtt_params["password"]
        )
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
        # whenever a message is received, the data should be stored in a dict with topic as key and payload as value, this dict should be used to get the data in the get_data_from_mqtt function
        if not hasattr(self, "message_store"):
            self.mqtt_message_store = {}
        self.mqtt_message_store[message.topic] = message.payload.decode()

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

    def get_data_from_mqtt(
        self,
        method: DataQueryTypes,
        entity: InputModel,
    ) -> Union[InputDataEntityModel, None]:
        """
        Function to get the data from the mqtt broker

        Args:
            method (DataQueryTypes): Keyword for type of query
            entity (InputModel): Input entity

        Returns:
            Union[InputDataEntityModel, None]: Model with the input data or None if no data is available
        """

        pass

    def _get_last_timestamp_for_mqtt_output(
        self, output_entity: OutputModel
    ) -> tuple[OutputDataEntityModel, Union[datetime, None]]:
        """
        Function to get the latest timestamps of the output entity from a MQTT message, if exitst

        Args:
            output_entity (OutputModel): Output entity

        Returns:
            tuple[OutputDataEntityModel, Union[datetime, None]]:
                - OutputDataEntityModel with timestamps for the attributes
                - the latest timestamp of the output entity for the attribute
                with the oldest value (None if no timestamp is available)
        TODO:
            - is it really nessesary to get a timestamp for MQTT-calculations /
            during calculation time is set to input_time
        """

        output_id = output_entity.id_interface

        timestamps = []
        timestamp_latest_output = None

        return (
            OutputDataEntityModel(id=output_id, attributes_status=timestamps),
            timestamp_latest_output,
        )
