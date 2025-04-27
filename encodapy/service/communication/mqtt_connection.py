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
from loguru import logger
from paho.mqtt.enums import CallbackAPIVersion

from encodapy.config import (
    ConfigModel,
    DataQueryTypes,
    DefaultEnvVariables,
    InputModel,
    Interfaces,
    OutputModel,
)
from encodapy.utils.error_handling import ConfigError, NotSupportedError
from encodapy.utils.models import (
    InputDataAttributeModel,
    InputDataEntityModel,
    OutputDataEntityModel,
)


class MqttConnection:
    """
    Class for the connection to a MQTT broker.
    Only a helper class.
    """

    def __init__(self) -> None:
        self.mqtt_params = {}
        # make ConfigModel-Class available in the MqttConnection-Class
        self.config: ConfigModel

    def load_mqtt_params(self) -> None:
        """
        Function to load the MQTT parameters from the environment variables
        or use the default values from the DefaultEnvVariables class.
        """
        # the IP of the broker
        self.mqtt_params["broker"] = os.environ.get(
            "MQTT_BROKER", DefaultEnvVariables.MQTT_BROKER.value
        )
        # the port of the broker
        self.mqtt_params["port"] = int(
            os.environ.get("MQTT_PORT", DefaultEnvVariables.MQTT_PORT.value)
        )
        # the username to connect to the broker
        self.mqtt_params["username"] = os.environ.get(
            "MQTT_USERNAME", DefaultEnvVariables.MQTT_USERNAME.value
        )
        # the password to connect to the broker
        self.mqtt_params["password"] = os.environ.get(
            "MQTT_PASSWORD", DefaultEnvVariables.MQTT_PASSWORD.value
        )
        # the topic prefix to use for the topics
        self.mqtt_params["topic_prefix"] = os.environ.get(
            "MQTT_TOPIC_PREFIX", DefaultEnvVariables.MQTT_TOPIC_PREFIX.value
        )

        if not self.mqtt_params["broker"] or not self.mqtt_params["port"]:
            raise ConfigError("MQTT broker and port must be set")

    def prepare_mqtt_connection(self) -> None:
        """
        Function to prepare the MQTT connection
        """
        # initialize the MQTT client
        self.mqtt_client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)

        # set username and password for the MQTT client
        self.mqtt_client.username_pw_set(
            self.mqtt_params["username"], self.mqtt_params["password"]
        )

        # try to connect to the MQTT broker
        try:
            self.mqtt_client.connect(
                self.mqtt_params["broker"], self.mqtt_params["port"]
            )
        except Exception as e:
            raise ConfigError(
                f"Could not connect to MQTT broker {self.mqtt_params['broker']}:{self.mqtt_params['port']} with given login information - {e}"
            ) from e

        # prepare the message store
        self.prepare_mqtt_message_store()

    def prepare_mqtt_message_store(self) -> None:
        """
        Function to prepare the MQTT message store, subscribe to all topics from in- and outputs
        (means subscribes to controller itself) and set the default values
        """
        # this dict should be filled by on_messages (messages are stored with topic as key and payload as value)
        # and used to get the data in the get_data_from_mqtt function
        # TODO MB: one "mqtt_message_store" for all connections? or one for inputs/outputs?
        self.mqtt_message_store = {}

        # set the message store with default values for all mqtt attributes in config
        for entity in self.config.inputs + self.config.outputs:
            if entity.interface == Interfaces.MQTT:
                for attribute in entity.attributes:
                    # set the topic for the attribute
                    topic = self.assemble_topic_parts(
                        [
                            self.mqtt_params["topic_prefix"],
                            entity.id_interface,
                            attribute.id_interface,
                        ]
                    )

                    if topic in self.mqtt_message_store:
                        logger.warning(
                            f"prepare_mqtt_message_store: Topic {topic} from {entity.id} already exists in the message store. Overwriting value."
                        )

                    # set the default value for the attribute
                    if hasattr(attribute, "value"):
                        value = attribute.value
                    else:
                        value = None

                    self.mqtt_message_store[topic] = value
                    # TODO MB: check if e.g. timestamp is needed for the attribute
                    # TODO MB: check if the attribute is a timeseries or a value

    def assemble_topic_parts(self, parts: list[str]) -> str:
        """
        Function to build a topic path from a list of strings.
        Ensures that the resulting topic path is correctly formatted with exactly one '/' between parts.

        Args:
            parts (list[str]): List of strings to be joined into a topic path.

        Returns:
            str: The correctly formatted topic path.

        Raises:
            ValueError: If the resulting topic path is not correctly formatted.
        """
        if not parts:
            raise ValueError("The list of parts cannot be empty.")

        # Join the parts with a single '/', stripping leading/trailing slashes from each part to avoid double slashes in the topic path
        topic_path = "/".join(part.strip("/") for part in parts)

        return topic_path

    def publish(self, topic, payload) -> None:
        """
        Function to publish a message to a topic
        """
        if not self.mqtt_client:
            raise NotSupportedError(
                "MQTT client is not prepared. Call prepare_mqtt_connection first."
            )
        self.mqtt_client.publish(topic, payload)

    def subscribe(self, topic):
        """
        Function to subscribe to a topic
        """
        if not self.mqtt_client:
            raise NotSupportedError(
                "MQTT client is not prepared. Call prepare_mqtt_connection first."
            )
        self.mqtt_client.subscribe(topic)

    def on_message(self, client, userdata, message):
        """
        Callback function for received messages, stores the message in the message store
        """
        if not hasattr(self, "mqtt_message_store"):
            raise NotSupportedError(
                "MQTT message store is not initialized. Call prepare_mqtt_connection first."
            )
        self.mqtt_message_store[message.topic] = message.payload.decode()

    def start(self):
        """
        Function to hang in on_message hook and start the MQTT client loop
        """
        if not hasattr(self, "mqtt_client") or self.mqtt_client is None:
            raise NotSupportedError(
                "MQTT client is not prepared. Call prepare_mqtt_connection first."
            )

        if hasattr(self, "_mqtt_loop_running") and self._mqtt_loop_running:
            raise NotSupportedError("MQTT client loop is already running.")

        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.loop_start()
        self._mqtt_loop_running = True  # state variable to check if the loop is running

    def stop(self):
        """
        Function to stop the MQTT client loop and clean up resources
        """
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()

    def get_data_from_mqtt(
        self,
        method: DataQueryTypes,
        entity: InputModel,
    ) -> Union[InputDataEntityModel, None]:
        """
        Function to get the data from the MQTT broker

        Args:
            method (DataQueryTypes): Keyword for type of query
            entity (InputModel): Input entity

        Returns:
            Union[InputDataEntityModel, None]: Model with the input data or None if no data is available
        """
        if not hasattr(self, "mqtt_message_store"):
            raise NotSupportedError(
                "MQTT message store is not initialized. Call prepare_mqtt_connection first."
            )

        attributes_values = []

        for attribute in entity.attributes:
            topic = (
                attribute.id_interface  # TODO MB: build the full topic
            )  # Use the attribute's interface ID as the topic
            if topic not in self.mqtt_message_store:  # init each topic with None
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
