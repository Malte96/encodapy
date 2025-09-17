"""
Defines the NewComponent class.
"""

from typing import Optional, Union

from loguru import logger

from encodapy.components.basic_component import BasicComponent, StaticDataEntityModel
from encodapy.config.models import ControllerComponentModel
from encodapy.utils.datapoints import DataPointNumber
from encodapy.utils.units import DataUnits

from .new_component_config import (
    NewComponentConfigData,
    NewComponentInputData,
    NewComponentOutputData,
)


class NewComponent(BasicComponent):
    """
    Class for a new component
    """

    def __init__(
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
        static_data: Optional[list[StaticDataEntityModel]] = None,
    ) -> None:
        # Add the necessary instance variables here
        self.example_variable: float = 1

        # Add the type declaration for the following variables so that autofill works properly
        self.config_data: NewComponentConfigData
        self.input_data: NewComponentInputData
        self.output_data: NewComponentOutputData

        # Prepare Basic Parts / needs to be the latest part
        super().__init__(
            config=config, component_id=component_id, static_data=static_data
        )

        # Component-specific initialization logic

    def prepare_component(self) -> None:
        """
        Prepare the component (e.g., initialize resources)
        """
        logger.debug("Hello from NewComponent! Preparing...")

    def calculate_a_result(self) -> DataPointNumber:
        """
        Example calculation function for the new component
        """
        # Example calculation logic using the input data stored in the component
        logger.debug("Calculating a_result in NewComponent...")
        a_number = 13.0

        return DataPointNumber(value=a_number, unit=DataUnits.DEGREECELSIUS)

    def calculate_another_result(self) -> DataPointNumber:
        """
        Example calculation function for the new component
        """
        # Example calculation logic using the input data stored in the component
        logger.debug("Calculating another_result in NewComponent...")
        another_number = (
            42
            if self.input_data.another_number_input.value is None
            else self.input_data.another_number_input.value
        )
        return DataPointNumber(value=another_number, unit=DataUnits.DEGREECELSIUS)

    def calculate(self) -> None:
        """
        Perform the calculations for the new component
        """
        logger.debug("Calculating in NewComponent...")

        self.output_data = NewComponentOutputData(
            result=self.calculate_a_result(),
            optional_result=self.calculate_another_result(),
        )
