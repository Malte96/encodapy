"""
Description: This file contains the class MqttConnection,
which is used to store the connection parameters for the MQTT broker.
Author: Maximilian Beyer
"""

import json
import os
from datetime import datetime
from typing import Union

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from encodapy.config import DataQueryTypes, DefaultEnvVariables, InputModel, OutputModel
from encodapy.utils.error_handling import ConfigError, NotSupportedError
from encodapy.utils.models import (
    InputDataAttributeModel,
    InputDataEntityModel,
    OutputDataEntityModel,
)


class MqttConnection:
    """
    Class for the connection to a mqtt broker.
    Only a helper class.
    """

    def __init__(self):
        self.mqtt_params = {}
        # TODO: Where to put together the topic-parts?

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
        self.mqtt_client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
        self.mqtt_client.username_pw_set(
            self.mqtt_params["username"], self.mqtt_params["password"]
        )
        self.mqtt_client.connect(self.mqtt_params["broker"], self.mqtt_params["port"])

    def publish(self, topic, payload):
        """
        Function to publish a message to a topic
        """
        if not self.mqtt_client:
            raise NotSupportedError("MQTT client is not connected")
        self.mqtt_client.publish(topic, payload)

    def subscribe(self, topic):
        """
        Function to subscribe to a topic
        """
        if not self.mqtt_client:
            raise NotSupportedError("MQTT client is not connected")
        self.mqtt_client.subscribe(topic)

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
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.loop_start()

    def stop(self):
        """
        Function to stop the mqtt client loop
        """
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()

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
        if not hasattr(self, "mqtt_message_store"):
            raise NotSupportedError(
                "MQTT message store is not initialized. Start the MQTT client first."
            )

        attributes_values = []

        for attribute in entity.attributes:
            topic = (
                attribute.id_interface
            )  # Use the attribute's interface ID as the topic
            if topic not in self.mqtt_message_store:
                # If the topic is not in the message store, mark the data as unavailable
                attributes_values.append(
                    InputDataAttributeModel(
                        id=attribute.id,
                        data=None,
                        data_type=attribute.type,
                        data_available=False,
                        latest_timestamp_input=None,
                        unit=None,
                    )
                )
                continue

            # Decode the message payload and extract the data
            message_payload = self.mqtt_message_store[topic]
            try:
                # Parse the payload (assuming JSON format for structured data)
                payload_data = json.loads(message_payload)
                data_value = payload_data.get("value", None)
                timestamp = payload_data.get("timestamp", None)

                # Convert timestamp to datetime if available
                if timestamp:
                    timestamp = datetime.fromisoformat(timestamp)

                attributes_values.append(
                    InputDataAttributeModel(
                        id=attribute.id,
                        data=data_value,
                        data_type=attribute.type,
                        data_available=True,
                        latest_timestamp_input=timestamp,
                        unit=None,  # Add unit handling if necessary
                    )
                )
            except (json.JSONDecodeError, KeyError):
                # Handle invalid or missing data in the payload
                attributes_values.append(
                    InputDataAttributeModel(
                        id=attribute.id,
                        data=None,
                        data_type=attribute.type,
                        data_available=False,
                        latest_timestamp_input=None,
                        unit=None,
                    )
                )

        return InputDataEntityModel(id=entity.id, attributes=attributes_values)

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
