"""
Description: This module contains the definition of a service to calculate \
    the energy in a thermal storage based on the temperature sensors.
Author: Martin Altenburger
"""
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
from loguru import logger
from encodapy.components.components_basic_config import IOAllocationModel
from encodapy.components.thermal_storage import ThermalStorage
from encodapy.service import ControllerBasicService
from encodapy.utils.models import (
    InputDataModel,
    DataTransferModel,
    DataTransferComponentModel
    )

class ThermalStorageCalculations(Enum):
    """
    Definition of the names of the thermal storage results & functions for the calculations
    
    Contains:
        `STORAGE_ENERGY` ("storage__energy"): The energy stored in the thermal storage
        `STORAGE_LEVEL` ("storage__level"): The current level of the thermal storage
        `STORAGE_LOADING_POTENTIAL` ("storage__loading_potential"): \
            The potential for loading energy into the thermal storage
    """
    STORAGE_ENERGY = ("storage__energy", "get_storage_energy_current")
    STORAGE_LEVEL = ("storage__level", "calculate_state_of_charge")
    STORAGE_LOADING_POTENTIAL = ("storage__loading_potential", "get_storage_loading_potential")

    def __init__(self, result, calculation):
        self._result = result
        self._calculation = calculation

    @classmethod
    def from_result(cls, result:str):
        """
        Create a ThermalStorageCalculations member from a result name.

        Args:
            result (str): The result name to match.

        Raises:
            ValueError: If the result name is not found.

        Returns:
            ThermalStorageCalculations: The matching enum member.
        """
        for member in cls:
            if member.result == result:
                return member
        logger.error(f"Result '{result}' not found in ThermalStorageCalculations")
        return None

    @property
    def result(self):
        """
        Returns the result name of the thermal storage calculation.
        """
        return self._result

    @property
    def calculation(self):
        """
        Returns the calculation function name of the thermal storage calculation.
        """
        return self._calculation

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

        components = []

        for output_datapoint_name, _ in self.thermal_storage.io_model.output.model_fields.items():

            output_datapoint_config: Optional[IOAllocationModel] = getattr(
                self.thermal_storage.io_model.output,
                output_datapoint_name)

            if output_datapoint_config is None:
                continue

            calculation_function = ThermalStorageCalculations.from_result(output_datapoint_name)

            if calculation_function is None:
                continue

            result_value, result_unit = getattr(self.thermal_storage, calculation_function.calculation)()
            # in Klasse mit self

            components.append(DataTransferComponentModel(
                entity_id=output_datapoint_config.entity,
                attribute_id=output_datapoint_config.attribute,
                value=result_value,
                unit=result_unit,
                timestamp=datetime.now(timezone.utc)
            ))
            # TODO was ist mit der unit?
            logger.debug(f"Calculated {output_datapoint_name}: {result_value} {result_unit}")

            #TODO hier die Verknüpfung aus dem Intranet:
            # https://intranet.tu-dresden.de/spaces/teamGEWV/pages/456884657/2025-08-12+Besprechungsnotizen

        print(components)

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
