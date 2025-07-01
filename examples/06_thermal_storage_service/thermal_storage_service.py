"""
Description: This module contains the definition of a service to calculate \
    the energy in a thermal storage based on the temperature sensors.
Author: Martin Altenburger
"""
from datetime import datetime, timezone
from encodapy.service import ControllerBasicService
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

    async def calculation(self,
                          data: InputDataModel
                          ):
        """
        Function to do the calculation
        Args:
            data (InputDataModel): Input data with the measured values for the calculation
        """

        inputs = {}
        for input_key, input_config in self.heater_config.inputs.items():
            inputs[input_key] = self.get_input_values(input_entities=data.input_entities,
                                                      input_config=input_config)

        #TODO Thermal Storage einbinden
        # thermal_storage = 

        return DataTransferModel(components=[
            DataTransferComponentModel(
                entity_id=,
                attribute_id=,
                value=,
                timestamp=datetime.now(timezone.utc))
                    ]
                )
