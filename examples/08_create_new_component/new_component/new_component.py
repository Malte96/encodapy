from typing import Union

from loguru import logger

from encodapy.components.basic_component import BasicComponent
from encodapy.components.basic_component_config import ControllerComponentStaticData
from encodapy.config.models import ControllerComponentModel
from encodapy.utils.models import InputDataModel
from encodapy.utils.units import DataUnits


class NewComponent(BasicComponent):
    """
    Class for a new component
    """

    # Inputs:
    a_input: float
    another_input: float
    optional_input: float

    # Outputs:
    a_result: float
    another_result: float

    def __init__(
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
        static_data: ControllerComponentStaticData,  # TODO: Redesign desired
    ) -> None:
        # Add the necessary instance variables here (you need to store the input data in the component) TODO: Is that so?
        # example: self.variable: Optional[float]
        self.static_data = static_data

        super().__init__(config=config, component_id=component_id)

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
        # a_number = self.a_input + self.another_input
        return a_number, DataUnits.KELVIN

    def calculate_another_result(self) -> tuple[float, DataUnits]:
        """
        Example calculation function for the new component
        """
        # Example calculation logic using the input data stored in the component
        logger.debug("Calculating another_result in NewComponent...")
        another_number = 42 if self.another_input is None else self.another_input
        return another_number, DataUnits.DEGREECELSIUS
