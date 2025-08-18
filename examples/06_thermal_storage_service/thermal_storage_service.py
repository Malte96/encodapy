"""
Description: This module contains the definition of a service to calculate \
    the energy in a thermal storage based on the temperature sensors.
Author: Martin Altenburger
"""
from datetime import datetime, timezone
from enum import Enum
from loguru import logger
from encodapy.components.thermal_storage import ThermalStorage
from encodapy.service import ControllerBasicService
from encodapy.utils.models import (
    InputDataModel,
    DataTransferModel,
    DataTransferComponentModel
    )

class ThermalStorageResults(Enum):
    """
    Definition of the thermal storage results
    TODO: welche Varianten brauchen wir?
    
    Contains:
        `STORAGE_ENERGY` ("storage__energy"): The energy stored in the thermal storage
        `STORAGE_LEVEL` ("storage__level"): The current level of the thermal storage
        `STORAGE_LOADING_POTENTIAL` ("storage__loading_potential"): \
            The potential for loading energy into the thermal storage
    """
    STORAGE_ENERGY = "storage__energy"
    STORAGE_LEVEL = "storage__level"
    STORAGE_LOADING_POTENTIAL = "storage__loading_potential"

class ThermalStorageCalculations(Enum):
    """
    Definition of the names of the thermal storage calculations
    """
    STORAGE_ENERGY = "get_storage_energy_current"
    STORAGE_LEVEL = "calculate_state_of_charge"
    STORAGE_LOADING_POTENTIAL = "get_storage_loading_potential" #TODO is missing

class ThermalStorageService(ControllerBasicService):
    """
    Class for a thermal storage calculation service

    """

    def __init__(self)-> None:
        """
        Constructor for the ThermalStorageService
        """
        self.thermal_storage: ThermalStorage
        super().__init__()

    def prepare_start(self):
        """ Function to prepare the thermal storage service for start
        This function loads the thermal storage configuration \
            and initializes the thermal storage component.
        """

        self.thermal_storage = ThermalStorage(
            config=self.config.controller_components,
            component_id="thermal_storage",
            static_data=self.staticdata
            )


    async def calculation(self,
                          data: InputDataModel
                          )-> DataTransferModel:
        """
        Function to do the calculation

        Args:
            data (InputDataModel): Input data with the measured values for the calculation
        """
        if self.thermal_storage.io_model is None:
            logger.warning("Thermal storage IO model is not set.")
            return DataTransferModel(components=[])

        self.thermal_storage.set_temperature_values(input_entities=data.input_entities)

        storage__energy = self.thermal_storage.get_storage_energy_current()
        storage__level = self.thermal_storage.calculate_state_of_charge()
        logger.debug("Energy Storage Level: " + str(storage__level) + " %")
        logger.debug("Energy of the Storage: " + str(storage__energy) + " Wh")

        components = []

        for output_datapoint_name, output_datapoint_config in self.thermal_storage.io_model.output.__dict__.items():
            print(output_datapoint_name, output_datapoint_config)
            if output_datapoint_config is None:
                continue
            result_name = ThermalStorageResults(output_datapoint_name)
            print(result_name)
            # function_name = ThermalStorageCalculations(result_name).value
            # print(function_name)
            #TODO hier die Verknüpfung aus dem Intranet: https://intranet.tu-dresden.de/spaces/teamGEWV/pages/456884657/2025-08-12+Besprechungsnotizen
            # results = globals()[function_name]()
            # [getattr(CONTROL_COMPONENTS_CLASSES, CONTROL_COMPONENTS(component["type"]).name, None).value]

        # pylint problems see: https://github.com/pylint-dev/pylint/issues/4899
        if self.thermal_storage.io_model.output.storage__level is not None:  # pylint: disable=no-member
            components.append(DataTransferComponentModel(
                entity_id=self.thermal_storage.io_model.output.storage__level.entity,  # pylint: disable=no-member
                attribute_id=self.thermal_storage.io_model.output.storage__level.attribute,  # pylint: disable=no-member
                value=storage__level,
                timestamp=datetime.now(timezone.utc)
            ))

        if self.thermal_storage.io_model.output.storage__energy is not None:  # pylint: disable=no-member
            components.append(DataTransferComponentModel(
                entity_id=self.thermal_storage.io_model.output.storage__energy.entity,  # pylint: disable=no-member
                attribute_id=self.thermal_storage.io_model.output.storage__energy.attribute,  # pylint: disable=no-member
                value=storage__energy,
                timestamp=datetime.now(timezone.utc)
            ))

        return DataTransferModel(components=components)


    async def calibration(self,
                          data: InputDataModel
                          )-> None:
        """
        Function to do the calibration of the thermal storage service. 
        This function prepares the thermal storage component with the static data, \
            if this is reloaded.
        It is possible to update the static data of the thermal storage component with \
            rerunning the `prepare_start_thermal_storage` method with new static data.

        Args:
            data (InputDataModel): InputDataModel for the thermal storage component
        """
        if self.reload_staticdata:
            logger.debug("Reloading static data for thermal storage")
            self.thermal_storage.prepare_start_thermal_storage(static_data=data.static_entities)
