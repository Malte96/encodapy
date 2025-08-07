"""
Description: This file contains the class MqttConnection,
which is used to store the connection parameters for the MQTT broker.
Author: Maximilian Beyer
"""

import json
import os
import time
from datetime import datetime
from typing import Optional, Union

import paho.mqtt.client as mqtt
from loguru import logger
from paho.mqtt.enums import CallbackAPIVersion
from pandas import DataFrame

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
    AttributeModel,
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
        """
        Constructor for the MqttConnection class.
        Initializes the MQTT parameters and the MQTT client.
        """
        self.mqtt_params: dict = {}
        self.config: ConfigModel
        self.mqtt_client: Optional[mqtt.Client] = None
        self.mqtt_message_store: dict[str, dict] = {}
        self._mqtt_loop_running = False

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
        if not self.mqtt_client:
            self.mqtt_client = mqtt.Client(
                callback_api_version=CallbackAPIVersion.VERSION2
            )

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
                f"Could not connect to MQTT broker {self.mqtt_params['broker']}:"
                f"{self.mqtt_params['port']} with given login information - {e}"
            ) from e

        # prepare the message store
        self.prepare_mqtt_message_store()

        # subscribe to all topics in the message store
        self.subscribe_to_message_store_topics()

        # start the MQTT client loop
        self.start_mqtt_client()

    def prepare_mqtt_message_store(self) -> None:
        """
        Function to prepare the MQTT message store for all in- and outputs and set the default
        values for all attributes of the entities in the config.

        Format of the message store:
        {
            "topic": {
                "entity_id": "entity_id",
                "entity_type": "input/output",
                "attribute_id": "attribute_id",
                "payload": value,
                "timestamp": datetime.now(),
            }
        }
        """
        if self.mqtt_message_store:
            logger.warning("MQTT message store is not empty and will be overwritten.")
            self.mqtt_message_store.clear()

        # check if the config is set
        if self.config is None:
            raise ConfigError(
                "ConfigModel is not set. Please set the config before using the MQTT connection."
            )

        # set the message store with default values for all mqtt entities and their attributes
        for entity in self.config.inputs + self.config.outputs:
            if entity.interface == Interfaces.MQTT:
                # add the entity itself to the message store
                topic = self.assemble_topic_parts(
                    [self.mqtt_params["topic_prefix"], entity.id_interface]
                )

                if entity in self.config.inputs:
                    entity_type = "input"
                elif entity in self.config.outputs:
                    entity_type = "output"
                else:
                    raise ValueError(
                        f"Entity {entity.id} is neither an input nor an output. "
                        "This should not happen."
                    )

                self._add_item_to_mqtt_message_store(
                    topic=topic,
                    entity_id=entity.id,
                    entity_type=entity_type,
                )

                # iterate over all attributes of the entity and add them to the message store
                for attribute in entity.attributes:
                    topic = self.assemble_topic_parts(
                        [
                            self.mqtt_params["topic_prefix"],
                            entity.id_interface,
                            attribute.id_interface,
                        ]
                    )

                    # set the default value for the attribute
                    if hasattr(attribute, "value"):
                        default_value = attribute.value
                    else:
                        default_value = None

                    self._add_item_to_mqtt_message_store(
                        topic=topic,
                        entity_id=entity.id,
                        entity_type=entity_type,
                        attribute_id=attribute.id,
                        payload=default_value,
                    )

                    # wait 0.1 seconds to avoid flooding the MQTT broker with messages
                    # (especially if there are many attributes)
                    time.sleep(1)

    def assemble_topic_parts(self, parts: list[str | None]) -> str:
        """
        Function to build a topic from a list of strings.
        Ensures that the resulting topic is correctly formatted with exactly one '/' between parts.

        Args:
            parts (list[str|None]): List of strings to be joined into a topic.

        Returns:
            str: The correctly formatted topic.

        Raises:
            ValueError: If the resulting topic is not correctly formatted.
        """
        if not parts:
            raise ValueError("The list of parts cannot be empty.")

        # drop a part if it is None or empty
        parts = [part for part in parts if part not in (None, "")]

        # Join the parts with a single '/',
        # stripping only trailing slashes from each part to avoid double slashes in the topic
        topic = "/".join(part.rstrip("/") for part in parts if isinstance(part, str))

        return topic

    def _add_item_to_mqtt_message_store(
        self,
        *,
        topic: str,
        entity_id: str,
        entity_type: str,
        attribute_id: Optional[str] = None,
        payload=None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Function to add an item to the MQTT message store.
        If the topic already exists, it will be overwritten.
        Args:
            topic (str): The topic to add the item to.
            entity_id (str): The ID of the entity.
            entity_type (str): The type of the entity (input/output).
            attribute_id (Optional[str]): The ID of the attribute (if applicable).
            payload: The default value of the message (if applicable).
            timestamp (Optional[datetime]): The initial timestamp of the message (if applicable).
        """
        if topic in self.mqtt_message_store:
            logger.warning(
                f"Topic {topic} from {entity_id} already exists in message store, "
                "overwriting it. This should not happen, check your configuration."
            )

        self.mqtt_message_store[topic] = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "attribute_id": attribute_id,
            "payload": payload,
            "timestamp": timestamp,
        }

    def publish(
        self,
        topic: str,
        payload: Union[str, float, int, bool, dict, list, DataFrame, None],
    ) -> None:
        """
        Function to publish a message (payload) to a topic.

        Every payload is converted to a utf8 encoded string before publishing
        (at the latest from the paho-mqtt package used).

        Args:
            topic (str): The topic to publish the message to
            payload (Union[str, float, int, bool, dict, list, DataFrame, None]): payload to publish
        """
        if not self.mqtt_client:
            raise NotSupportedError(
                "MQTT client is not prepared. Call prepare_mqtt_connection() first."
            )

        # prepare the payload for publishing
        payload = self.prepare_payload_for_publish(payload)

        # publish the message to the topic
        self.mqtt_client.publish(topic, payload)
        logger.debug(f"Published to topic {topic}: {payload}")

    def prepare_payload_for_publish(self, payload) -> Union[str, None]:
        """
        Function to prepare the payload for publishing.

        Converts the payload to a JSON string if it is a dict, list or DataFrame.
        If the payload is a string, float, int or bool, it is converted to a string.
        If the payload is None or an unsupported type, it is set to None.
        """

        payload = None

        try:
            if isinstance(payload, (dict, list)):
                payload = json.dumps(payload)
            elif isinstance(payload, DataFrame):
                payload = payload.to_json()
            elif isinstance(payload, (str, float, int, bool)):
                payload = str(payload)
            else:
                logger.warning(
                    f"Unsupported payload type: {type(payload)}, set it to None"
                )
        except TypeError as e:
            logger.warning(f"Failed to convert payload: {e}, set it to None")

        return payload

    def subscribe(self, topic) -> None:
        """
        Function to subscribe to a topic
        """
        if not self.mqtt_client:
            raise NotSupportedError(
                "MQTT client is not prepared. Call prepare_mqtt_connection() first."
            )
        self.mqtt_client.subscribe(topic)

    def subscribe_to_message_store_topics(self) -> None:
        """
        Function to subscribe to all topics in the message store.
        """
        if not self.mqtt_message_store:
            raise NotSupportedError(
                "MQTT message store is initialized, but empty. Cannot subscribe to topics."
            )

        for topic in self.mqtt_message_store:
            self.subscribe(topic)
            logger.debug(f"Subscribed to topic: {topic}")

    def on_message(self, _, __, message):
        """
        Callback function for received messages, stores the decoded message with its timestamp
        in the message store.
        """
        if not hasattr(self, "mqtt_message_store"):
            raise NotSupportedError(
                "MQTT message store is not initialized. Call prepare_mqtt_connection() first."
            )
        # save the time from receiving the message
        current_time = datetime.now()
        logger.debug(
            f"MQTT connection received message on {message.topic} at {current_time}"
        )

        if message.topic in self.mqtt_message_store:
            # decode the message payload
            try:
                payload = message.payload.decode("utf-8")
            except UnicodeDecodeError as e:
                logger.error(f"Failed to decode message payload: {e}")
                return

            # store payload and current time in the message store
            self.mqtt_message_store[message.topic]["payload"] = payload
            self.mqtt_message_store[message.topic]["timestamp"] = current_time

            logger.debug(
                f"Updated MQTT message store for topic {message.topic} with value: {payload} "
                f"and timestamp: {current_time}"
            )

            # if the item in the store is from an entity, its attribute_id in the store must be None
            # and attribute values are possibly in payload
            if self.mqtt_message_store[message.topic]["attribute_id"] is None:
                # get the entity from the message store
                entity_id = self.mqtt_message_store[message.topic]["entity_id"]
                logger.debug(
                    f"MQTT message was received at topic from entity {entity_id}, "
                    "try to scan payload for attributes."
                )
                # try to parse the payload as JSON
                try:
                    payload = json.loads(payload)
                    self._extract_attributes_from_payload_and_update_store(
                        entity=entity_id, payload=payload, timestamp=current_time
                    )
                except json.JSONDecodeError:
                    logger.error(
                        f"Failed to decode JSON payload for topic {message.topic}: {payload}"
                    )
                    return

    def _extract_attributes_from_payload_and_update_store(
        self,
        entity: Union[InputModel, OutputModel],
        payload: dict,
        timestamp: datetime = datetime.now(),
    ) -> None:
        """
        Function to extract attributes from the payload and update the message store.
        This is called when a message is received on a topic that corresponds to an entity.

        Args:
            payload (dict): The payload received from the MQTT broker.
            timestamp (datetime): The timestamp when the message was received.
        """
        if not hasattr(self, "mqtt_message_store"):
            raise NotSupportedError(
                "MQTT message store is not initialized. Call prepare_mqtt_connection() first."
            )

        for key, value in payload.items():
            # search in the message store for a subtopic that matches the key and entity
            for topic, item in self.mqtt_message_store.items():
                # check if the item in the message store is from the entity
                if item["entity_id"] != entity.id:
                    continue

                # get subtopic (last part of the topic), which could reference the attribute.id_interface
                subtopic = topic.split("/")[-1] if "/" in topic else topic

                # if subtopic matches key in the payload from entity, update the message store
                if subtopic == key:
                    item["payload"] = value
                    item["timestamp"] = timestamp
                    logger.debug(
                        f"Updated MQTT message store for topic {topic} with value: {value}"
                    )
                    continue

    def start_mqtt_client(self):
        """
        Function to hang in on_message hook and start the MQTT client loop
        """
        if not hasattr(self, "mqtt_client") or self.mqtt_client is None:
            raise NotSupportedError(
                "MQTT client is not prepared. Call prepare_mqtt_connection() first."
            )

        if hasattr(self, "_mqtt_loop_running") and self._mqtt_loop_running:
            raise NotSupportedError("MQTT client loop is already running.")

        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.loop_start()
        self._mqtt_loop_running = True  # state variable to check if the loop is running

    def stop_mqtt_client(self):
        """
        Function to stop the MQTT client loop and clean up resources
        """
        if isinstance(self.mqtt_client, mqtt.Client) and self._mqtt_loop_running:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self._mqtt_loop_running = False

    def get_data_from_mqtt(
        self,
        method: DataQueryTypes,
        entity: InputModel,
    ) -> InputDataEntityModel:
        """
        Function to get the data from the MQTT broker.
        It checks the MQTT message store for the topics of the entity and its attributes.
        If the topic is found, it extracts the data from the message payload.
        If the topic is not found or the payload is not in the expected format,
        it sets the data to None and marks it as unavailable.

        Args:
            method (DataQueryTypes): The method is currently not used.
            entity (InputModel): Input entity

        Returns:
            InputDataEntityModel: Model with input data (data=None if no data available)
        """
        if not hasattr(self, "mqtt_message_store"):
            raise NotSupportedError(
                "MQTT message store is not initialized. Call prepare_mqtt_connection() first."
            )

        attributes_values = []

        for attribute in entity.attributes:
            # construct the topic for the attribute
            topic = self.assemble_topic_parts(
                [
                    self.mqtt_params["topic_prefix"],
                    entity.id_interface,
                    attribute.id_interface,
                ]
            )

            # if the topic is not in the message store, mark the data as unavailable
            if topic not in self.mqtt_message_store:
                logger.warning(
                    f"Topic {topic} not found in MQTT message store. Setting data as None and "
                    "unavailable. User should check for possible misconfiguration!"
                )
                data = None
                data_available = False
                timestamp = None

            # if the topic is in the message store, extract the data from message payload
            else:
                message_payload = self.mqtt_message_store[topic]["payload"]
                try:
                    data = self._extract_payload_value(message_payload)
                    data_available = True
                except ValueError as e:
                    logger.error(
                        f"Failed to extract payload value for topic {topic}: {e}. "
                        "Setting data as None and unavailable."
                    )
                    data = None
                    data_available = False

                # Get the timestamp from the message store
                timestamp = self.mqtt_message_store[topic]["timestamp"]

            attributes_values.append(
                InputDataAttributeModel(
                    id=attribute.id,
                    data=data,
                    data_type=attribute.type,
                    data_available=data_available,
                    latest_timestamp_input=timestamp,
                    unit=None,  # TODO MB: Add unit handling if necessary
                )
            )
        return InputDataEntityModel(id=entity.id, attributes=attributes_values)

    def send_data_to_mqtt(
        self,
        output_entity: OutputModel,
        output_attributes: list[AttributeModel],
        # output_commands: list[CommandModel],
    ) -> None:
        """
        Function to send the output data to MQTT (publish the data to the MQTT broker)

        Args:
            - output_entity: OutputModel with the output entity
            - output_attributes: list with the output attributes
        """
        if not hasattr(self, "mqtt_client"):
            raise NotSupportedError(
                "MQTT client is not prepared. Call prepare_mqtt_connection() first."
            )

        # check if the config is set
        if self.config is None:
            raise ConfigError(
                "ConfigModel is not set. Please set the config before using the MQTT connection."
            )

        # publish the data to the MQTT broker
        for attribute in output_attributes:
            topic = self.assemble_topic_parts(
                [
                    self.mqtt_params["topic_prefix"],
                    output_entity.id_interface,
                    attribute.id_interface,
                ]
            )
            payload = attribute.value
            self.publish(topic, payload)

    def _extract_payload_value(
        self, payload
    ) -> Union[str, float, int, bool, dict, list, DataFrame, None]:
        """
        Function to extract data from the payload as needed.
        """
        # Check if the payload is None or empty
        if payload is None or payload == "":
            return None

        # Check if the payload is a JSON string and try to parse it
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                # If the payload is not a valid JSON but a string, split first string part as value
                # (workaround for cases where payload is a string from number and unit, e.g. 22 °C)
                # Added strip() to remove leading/trailing spaces (e.g., " 6552.0 h")
                payload = payload.strip().split(" ")[0]

        # If the payload is a valid JSON string or dict, extract the value from it if possible
        if isinstance(payload, dict):
            # Ensure case-insensitive key check
            if "value" in {k.lower() for k in payload.keys()}:
                # Search for actual key that is (case-insensitive) "value" and extract its value
                for k in payload.keys():
                    if k.lower() == "value":
                        value = payload[k]
                        break
                else:
                    raise ValueError(
                        f"Invalid payload format: 'value' key not found in payload {payload}"
                    )
            else:
                raise ValueError(
                    f"Invalid payload format: 'value' key not found in payload {payload}"
                )
        # If the payload itself is a number, boolean or string, use it directly
        elif isinstance(payload, (float, int, str, bool)):
            value = payload
        else:
            raise ValueError(f"Invalid payload format: {type(payload)}")

        # if remaining value is bool, return it
        if isinstance(value, bool):
            return value

        # else try to convert it to float
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(
                f"Invalid data type for payload value: {type(value)}"
            ) from exc

    def _get_last_timestamp_for_mqtt_output(
        self, output_entity: OutputModel
    ) -> tuple[OutputDataEntityModel, Union[datetime, None]]:
        """
        Function to get the latest timestamps of the output entity from a MQTT message, if exists

        Args:
            output_entity (OutputModel): Output entity

        Returns:
            tuple[OutputDataEntityModel, Union[datetime, None]]:
                - OutputDataEntityModel with timestamps for the attributes
                - the latest timestamp of the output entity for the attribute
                with the oldest value (None if no timestamp is available)
        TODO:
            - Just here for compatibility with the old code, should be removed in the future
        """

        timestamps: list = []
        timestamp_latest_output = None

        return (
            OutputDataEntityModel(id=output_entity.id, attributes_status=timestamps),
            timestamp_latest_output,
        )
