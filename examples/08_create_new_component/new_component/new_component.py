from datetime import datetime
from typing import Optional, Union

from loguru import logger

from encodapy.components.basic_component import BasicComponent, StaticDataEntityModel
from encodapy.components.basic_component_config import DataPointGeneral
from encodapy.config.models import ControllerComponentModel
from encodapy.utils.models import InputDataModel
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

    # # Inputs:
    # a_input: float
    # another_input: float
    # optional_input: float

    # # Outputs:
    # a_result: float
    # another_result: float

    def __init__(
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
        static_data: Optional[list[StaticDataEntityModel]] = None,
    ) -> None:
        # Add the necessary instance variables here (you need to store the input data in the component)
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
        pass

    def set_input_values(self, input_data: InputDataModel) -> None:
        """
        Set the input values for the new component
        """
        input_fields = self.component_config.inputs.root.keys()
        for field_name in input_fields:
            input_config = self.component_config.inputs.root[field_name]
            value, _unit = self.get_component_input(
                input_entities=input_data.input_entities, input_config=input_config
            )
            setattr(self, field_name, value)

    def calculate_a_result(self) -> tuple[float, DataUnits]:
        """
        Example calculation function for the new component
        """
        # Example calculation logic using the input data stored in the component
        logger.debug("Calculating a_result in NewComponent...")
        a_number = 13.0
        # TODO: SERVICE STOPS RUNNING: Calculate with None-values
        # a_number = (
        #     self.input_data.a_number_input.value
        #     + self.input_data.another_number_input.value
        # )
        return a_number, DataUnits.KELVIN

    def calculate_another_result(self) -> tuple[float, DataUnits]:
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
        return another_number, DataUnits.DEGREECELSIUS

    def calculate(self) -> None:
        """
        Perform the calculations for the new component
        """
        logger.debug("Calculating in NewComponent...")

        # Call the calculation functions and store the results in the output data model
        # self.output_data.a_result.value, self.output_data.a_result.unit = (
        #     self.calculate_a_result()
        # )
        # self.output_data.a_result.time = datetime.now()
        # self.output_data.a_result = DataPointGeneral(
        #     value=13, unit=DataUnits.KELVIN, time=datetime.now()
        # )
        a_result_datapoint = DataPointGeneral(
            value=13, unit=DataUnits.DEGREECELSIUS, time=datetime.now()
        )

        self.output_data = NewComponentOutputData(a_result=a_result_datapoint)
