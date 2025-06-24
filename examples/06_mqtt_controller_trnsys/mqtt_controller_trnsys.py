"""
Description: This module contains the definition of a small example service \
    in the form of a heat controller based on a two point controller with hysteresis.
Author: Martin Altenburger
"""

from datetime import datetime, timezone
from typing import Optional, Union

from loguru import logger

from encodapy.config.models import ControllerComponentModel, OutputModel
from encodapy.service import ControllerBasicService
from encodapy.utils.models import (
    DataTransferComponentModel,
    DataTransferModel,
    InputDataEntityModel,
    InputDataModel,
)


class MQTTControllerTrnsys(ControllerBasicService):
    """
    Class for a example service controller for Trnsys
    Service is used to control a hybrid plant with heat pump and pellet boiler
        - read the configuration
        - prepare the start of the service
        - start the service
        - receive the data
        - do the controlling calculation
        - send the data to the output
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller_config: Optional[ControllerComponentModel] = None
        self.controller_outputs_for_trnsys: Optional[OutputModel] = None

    async def prepare_start(self) -> None:
        """
        prepare the start of the trnsys controller service

        """
        logger.info("Prepare Start of Service")

        await self.prepare_basic_start()

        # add own functionality for the current service here
        self.controller_config = self.get_controller_config(
            type_name="system-controller"
        )
        self.controller_outputs_for_trnsys = self.get_output_config(
            output_entity="TRNSYS-Inputs"
        )

        logger.info("TRNSYS Controller Service prepared successfully")

    def get_controller_config(self, type_name: str) -> ControllerComponentModel:
        """
        Function to get the configuration of the heat controller

        Returns:
            dict: The configuration of the heat controller
        """
        if self.config is None:
            raise ValueError("No configuration found")

        for component in self.config.controller_components:
            if component.type == type_name:
                return component
        raise ValueError("No heat controller configuration found")

    def get_output_config(self, output_entity: str) -> OutputModel:
        """
        Function to get the output configuration for a specific entity

        Args:
            output_entity (str): The ID of the output entity

        Returns:
            OutputModel: The output configuration
        """
        if self.config is None:
            raise ValueError("No configuration found")

        for entity in self.config.outputs:
            if entity.id == output_entity:
                return entity
        raise ValueError("No output configuration found")

    def get_inputs(self, data: InputDataModel) -> tuple[dict, dict]:
        """
        Function to get the inputs from trnsys and the pellet boiler

        Returns:
            dict: The inputs of the heat controller
        """
        if self.controller_config is None:
            raise ValueError("No controller configuration found")

        trnsys_inputs = {}
        boiler_inputs = {}
        for input_key, input_config in self.controller_config.inputs.items():
            # check if the input is a TRNSYS input or a PB input
            if input_config["entity"] == "TRNSYS-Outputs":
                trnsys_inputs[input_key] = self.get_input_values(
                    input_entities=data.input_entities, input_config=input_config
                )
            elif input_config["entity"] == "PB-Outputs":
                boiler_inputs[input_key] = self.get_input_values(
                    input_entities=data.input_entities, input_config=input_config
                )

        return trnsys_inputs, boiler_inputs

    def get_input_values(
        self,
        input_entities: list[InputDataEntityModel],
        input_config: dict,
    ) -> Union[float, int, str, bool]:
        """
        Function to get the values of the input data

        Args:
            input_entities (list[InputDataEntityModel]): Data of input entities
            input_config (dict): Configuration of the input

        Returns:
            Union[float, int, str, bool]: The value of the input data
        """
        for input_data in input_entities:
            if input_data.id == input_config["entity"]:
                for attribute in input_data.attributes:
                    if attribute.id == input_config["attribute"]:
                        return attribute.data
        raise ValueError(f"Input data {input_config['entity']} not found")

    def check_heater_command(
        self,
        temperature_setpoint: float,
        temperature_measured: float,
        hysteresis: float,
        heater_status_old: int,
    ) -> int:
        """
        Function to check if the heater should be on or off \
            based on a 2 point controller with hysteresis

        Args:
            temperature_setpoint (float): The setpoint temperature
            temperature_measured (float): The measured temperature (acutal temperature)
            hysteresis (float): The hysteresis of the controller
            heater_status_old (bool): The old status of the heater

        Returns:
            bool: The new status of the heater
        """
        if temperature_measured < temperature_setpoint - hysteresis:
            return 1

        if temperature_measured > temperature_setpoint:
            return 0

        if (
            heater_status_old
            and temperature_measured > temperature_setpoint - hysteresis
        ):
            return 1

        return 0

    def check_inputs_not_empty(self, inputs: dict) -> bool:
        """
        Function to check if the MQTT message store is not False in any attribute.
        """
        for attribute_key, attribute_value in inputs.items():
            if attribute_value is False:
                logger.debug(
                    f"MQTT message store for attribute '{attribute_key}' is False"
                )
                return False
        return True

    async def calculation(self, data: InputDataModel) -> DataTransferModel:
        """
        Function to do the calculation
        Args:
            data (InputDataModel): Input data with the measured values for the calculation
        """

        # start loop to check if the TRNSYS MQTT messages in store are not None
        # while not self.check_inputs_not_empty(inputs=trnsys_inputs):
        #     logger.debug(
        #         "Waiting for MQTT messages from TRNSYS to be fully available in store..."
        #     )
        #     # HIER WIRD IMMER NUR NACH DEM WERT IN DER CONFIG GESCHAUT - Vergleich mit Bsp. 5 nötig
        #     time.sleep(0.01)

        # get the current inputs
        trnsys_inputs, boiler_inputs = self.get_inputs(data=data)

        # start loop to check if the TRNSYS MQTT messages in store are not None
        # while not self.check_mqtt_messages_from_trnsys_not_false(trnsys_inputs):
        #     logger.debug(
        #         "Waiting for MQTT messages from TRNSYS to be fully available in store..."
        #     )
        #     # HIER WIRD IMMER NUR NACH DEM WERT IN DER CONFIG GESCHAUT - Vergleich mit Bsp. 5 nötig
        #     time.sleep(0.01)

        # print(
        #     "TRNSYS MQTT messages are fully available in store, continue with calculation..."
        # )

        # add all output values to the output data (None for now)
        components = []
        sammeln_payload = ""

        for output_key, output_config in self.controller_config.outputs.items():
            if output_key == "full_trnsys_message":
                # skip the full output, it is handled separately
                continue

            entity_id = output_config["entity"]
            attribute_id = output_config["attribute"]

            # add standard message of the outputs to DataTransferComponentModel
            components.append(
                DataTransferComponentModel(
                    entity_id=entity_id,
                    attribute_id=attribute_id,
                    value=None,
                    timestamp=datetime.now(timezone.utc),
                )
            )

            # build the trnsys payload for the full message
            for output_attribute in self.controller_outputs_for_trnsys.attributes:
                if output_attribute.id == attribute_id:
                    trnsys_value = output_attribute.value
                    trnsys_variable_name = output_attribute.id_interface
                    sammeln_payload += f"{trnsys_variable_name} : {trnsys_value} # "

        # add trnsys full message to DataTransferComponentModel
        components.append(
            DataTransferComponentModel(
                entity_id="TRNSYS-Inputs",
                attribute_id="trnsys_sammeln",
                value=sammeln_payload,
                timestamp=datetime.now(timezone.utc),
            )
        )

        # set the trnsys mqtt messages in store to None
        # self.

        return DataTransferModel(components=components)

    async def calibration(self, data: InputDataModel):
        """
        Function to calibrate the model - here it is possible to adjust parameters it is necessary
        Args:
            data (InputDataModel): Input data for calibration
        """
        logger.debug("Calibration of the model is not necessary for this service")
        return
