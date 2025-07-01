"""
Description: This module contains the definition of a service to calculate \
    the energy in a thermal storage based on the temperature sensors.
Author: Martin Altenburger
"""
from typing import Union
from datetime import datetime, timezone
from loguru import logger
from pydantic import ValidationError

from encodapy.config.models import ControllerComponentModel
from encodapy.components.thermal_storage import ThermalStorage
from encodapy.components.thermal_storage_config import (
    ThermalStorageTemperatureSensors,
    IOAlocationModel,
    InputModel,
    OutputModel,
    ThermalStorageIO)
from encodapy.service import ControllerBasicService
from encodapy.utils.mediums import Medium
from encodapy.utils.models import (
    InputDataModel,
    InputDataEntityModel,
    DataTransferModel,
    DataTransferComponentModel
    )


class ThermalStorageService(ControllerBasicService):
    """
    Class for a thermal storage calculation service

    """

    def __init__(self):
        """
        Constructor for the ThermalStorageService
        """
        self.thermal_storage:ThermalStorage = None
        self.io_model:ThermalStorageIO = None
        super().__init__()

    def _load_thermal_storage_component(self)-> ControllerComponentModel:
        """
        Function to load the thermal storage configuration from the service configuration
        """
        for component in self.config.controller_components:
            if component.type == "thermal_storage":
                return component
        raise ValueError("No thermal storage configuration found")

    def _prepare_thermal_storage(self,
                                 config:ControllerComponentModel
                                 )-> ThermalStorage:
        """
        Function to prepare the thermal storage based on the configuration.

        Args:
            config (ControllerComponentModel): Configuration of the thermal storage component

        Raises:
            KeyError: Invalid medium in the configuration
            KeyError: No volume of the thermal storage specified in the configuration
            KeyError: No sensor configuration of the thermal storage specified in the configuration
            ValidationError: Invalid sensor configuration for the thermal storage

        Returns:
            ThermalStorage: Instance of the ThermalStorage class with the prepared configuration
        """

        medium_value = config.config.get("medium")
        if medium_value is None:
            error_msg = "No medium of the thermal storage specified in the configuration, \
                using default medium 'water'"
            logger.warning(error_msg)
            medium_value = 'water'
        try:
            medium:Medium = Medium(medium_value)
        except ValueError:
            error_msg = f"Invalid medium in the configuration: '{medium_value}'"
            logger.error(error_msg)
            raise ValueError(error_msg) from None

        storage_volume = config.config.get("volume")

        if storage_volume is None:
            error_msg = "No volume of the thermal storage specified in the configuration."
            logger.error(error_msg)
            raise KeyError(error_msg) from None

        sensor_config = config.config.get("sensor_config")
        if sensor_config is None:
            error_msg = "No sensor configuration of the thermal storage specified \
                in the configuration."
            logger.error(error_msg)
            raise KeyError(error_msg) from None

        try:
            sensor_config = ThermalStorageTemperatureSensors.model_validate(sensor_config)
        except ValidationError:
            error_msg = "Invalid sensor configuration in the thermal storage"
            logger.error(error_msg)
            raise

        return ThermalStorage(
            sensor_config=sensor_config,
            volume=storage_volume,
            medium=medium
        )

    def _prepare_i_o_config(self,
                            config:ControllerComponentModel
                            ):
        """
        Function to prepare the inputs and outputs of the service.
        This function is called before the service is started.
        """
        try:
            input_config = InputModel.model_validate(config.inputs)
        except ValidationError:
            error_msg = "Invalid input configuration for the thermal storage"
            logger.error(error_msg)
            raise

        try:
            output_config = OutputModel.model_validate(config.outputs)
        except ValidationError :
            error_msg = "Invalid output configuration for the thermal storage"
            logger.error(error_msg)
            raise

        self.io_model = ThermalStorageIO(
            input=input_config,
            output=output_config
            )

    def _check_input_configuration(self):
        """
        Function to check the input configuration of the service \
            in comparison to the sensor configuration.
        The inputs needs to match the sensor configuration.
        Raises:
            KeyError: If the input configuration does not match the sensor configuration
            Warning: If the input configuration does not match the sensor configuration,\
                but is not critical
        """
        # pylint problems see: https://github.com/pylint-dev/pylint/issues/4899
        if (self.thermal_storage.sensor_config.sensor_4_name is not None
            and self.io_model.input.temperature_4 is None): # pylint: disable=no-member
            error_msg = ("Input configuration does not match sensor configuration: "
                         "Sensor 4 is defined in the sensor configuration, "
                         "but not in the input configuration.")
            logger.error(error_msg)
            raise KeyError(error_msg)
        if (self.thermal_storage.sensor_config.sensor_5_name is not None
            and self.io_model.input.temperature_5 is None): # pylint: disable=no-member
            error_msg = ("Input configuration does not match sensor configuration: "
                         "Sensor 5 is defined in the sensor configuration, "
                         "but not in the input configuration.")
            logger.error(error_msg)
            raise KeyError(error_msg)

        if (self.thermal_storage.sensor_config.sensor_4_name is None
            and self.io_model.input.temperature_4 is not None): # pylint: disable=no-member
            logger.warning("Input configuration does not match sensor configuration: "
                           "Sensor 4 is defined in the input configuration, "
                           "but not in the sensor configuration."
                           "The sensor will not be used in the calculation.")
        if (self.thermal_storage.sensor_config.sensor_5_name is None
            and self.io_model.input.temperature_5 is not None): # pylint: disable=no-member
            logger.warning("Input configuration does not match sensor configuration: "
                           "Sensor 5 is defined in the input configuration, "
                           "but not in the sensor configuration."
                           "The sensor will not be used in the calculation.")


    def prepare_start(self):
        """
        Function to prepare the start of the service, \
            including the loading configuration of the service \
                and preparing the thermal storage.
        """

        thermal_storage_component = self._load_thermal_storage_component()

        self.thermal_storage = self._prepare_thermal_storage(config=thermal_storage_component)

        self._prepare_i_o_config(config=thermal_storage_component)

        self._check_input_configuration()


    def get_input_values(self,
                         input_entities:list[InputDataEntityModel],
                         input_config:IOAlocationModel,
                         )-> Union[float, int, str, bool]:
        """
        Function to get the values of the input data

        Args:
            input_entities (list[InputDataEntityModel]): Data of input entities
            input_config (dict): Configuration of the input

        Returns:
            Union[float, int, str, bool]: The value of the input data
        """
        for input_data in input_entities:
            if input_data.id == input_config.entity:
                for attribute in input_data.attributes:
                    if attribute.id == input_config.attribute:
                        return attribute.data
        raise ValueError(f"Input data {input_config['entity']} not found")

    async def calculation(self,
                          data: InputDataModel
                          ):
        """
        Function to do the calculation
        Args:
            data (InputDataModel): Input data with the measured values for the calculation
        """

        input_temperatures = {}

        for input_key, input_config in self.io_model.input.__dict__.items():
            if input_config is None:
                continue
            input_temperatures[input_key] = self.get_input_values(
                input_entities=data.input_entities,
                input_config=IOAlocationModel.model_validate(input_config))

        self.thermal_storage.set_temperature_values(temperature_values=input_temperatures)

        storage__level = self.thermal_storage.calculate_state_of_charge()

        storage__energy = self.thermal_storage.get_energy_content(storage__level)

        components = []

        # pylint problems see: https://github.com/pylint-dev/pylint/issues/4899
        if self.io_model.output.storage__level is not None:  # pylint: disable=no-member
            components.append(DataTransferComponentModel(
                entity_id=self.io_model.output.storage__level.entity,  # pylint: disable=no-member
                attribute_id=self.io_model.output.storage__level.attribute,  # pylint: disable=no-member
                value=storage__level,
                timestamp=datetime.now(timezone.utc)
            ))

        if self.io_model.output.storage__energy is not None:  # pylint: disable=no-member
            components.append(DataTransferComponentModel(
                entity_id=self.io_model.output.storage__energy.entity,  # pylint: disable=no-member
                attribute_id=self.io_model.output.storage__energy.attribute,  # pylint: disable=no-member
                value=storage__energy,
                timestamp=datetime.now(timezone.utc)
            ))

        return DataTransferModel(components=components)
