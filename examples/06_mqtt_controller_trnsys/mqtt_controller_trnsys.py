"""
Description: This module contains the definition of a small example service \
    in the form of a heat controller based on a two point controller with hysteresis.
Author: Martin Altenburger
"""

from datetime import datetime, timezone
from typing import Union

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

    def get_heat_controller_config(self) -> ControllerComponentModel:
        """
        Function to get the configuration of the heat controller

        Returns:
            dict: The configuration of the heat controller
        """
        if self.config is None:
            raise ValueError("No configuration found")

        for component in self.config.controller_components:
            if component.type == "heat_controller":
                return component
        raise ValueError("No heat controller configuration found")

    def get_output_config(self, output_entity: str) -> OutputModel:
        """
        Function to get the output of the configuration

        Returns:
            OutputModel: The output configuration
        """
        if self.config is None:
            raise ValueError("No configuration found")

        for entity in self.config.outputs:
            if entity.id == output_entity:
                return entity
        raise ValueError("No output configuration found")

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
        raise ValueError(
            f"Input data '{input_config['attribute']}' from entity '{input_config['entity']}' not found"
        )

    async def calculation(self, data: InputDataModel) -> DataTransferModel:
        """
        Function to do the calculation
        Args:
            data (InputDataModel): Input data with the measured values for the calculation
        """

        heater_config = self.get_heat_controller_config()
        controller_outputs = self.get_output_config(output_entity="system-controller")

        inputs = {}
        for input_key, input_config in heater_config.inputs.items():
            inputs[input_key] = self.get_input_values(
                input_entities=data.input_entities, input_config=input_config
            )

        # add all output values to the output data (None for now)
        components = []
        sammeln_payload = ""

        for output_key, output_config in heater_config.outputs.items():
            if output_key == "full_trnsys_message":
                # skip the full output, it is handled separately
                continue

            entity_id = output_config["entity"]
            attribute_id = output_config["attribute"]

            # add standard message of the output to DataTransferComponentModel
            components.append(
                DataTransferComponentModel(
                    entity_id=entity_id,
                    attribute_id=attribute_id,
                    value=None,
                    timestamp=datetime.now(timezone.utc),
                )
            )

            # build the trnsys payload for the full message
            for output_attribute in controller_outputs.attributes:
                if output_attribute.id == attribute_id:
                    controller_outputs_attribute = output_attribute
                    trnsys_value = controller_outputs_attribute.value
                    trnsys_variable_name = controller_outputs_attribute.id_interface
                    sammeln_payload += f"{trnsys_variable_name} : {trnsys_value} # "

        # add trnsys full message to DataTransferComponentModel
        components.append(
            DataTransferComponentModel(
                entity_id="system-controller",
                attribute_id="trnsys_sammeln",
                value=sammeln_payload,
                timestamp=datetime.now(timezone.utc),
            )
        )

        return DataTransferModel(components=components)

    async def calibration(self, data: InputDataModel):
        """
        Function to calibrate the model - here it is possible to adjust parameters it is necessary
        Args:
            data (InputDataModel): Input data for calibration
        """
        logger.debug("Calibration of the model is not necessary for this service")
        return
