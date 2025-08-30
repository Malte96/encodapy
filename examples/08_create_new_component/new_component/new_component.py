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

    def __init__(
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
        static_data: ControllerComponentStaticData,  # TODO: Redesign desired
    ) -> None:
        # Add the necessary instance variables here (you need to store the input data in the component)
        # example: self.variable: Optional[float]
        self.static_data = static_data

        super().__init__(config=config, component_id=component_id)

        # Component-specific initialization logic

    def prepare_component(self) -> None:
        """
        Prepare the component (e.g., initialize resources)
        """
        logger.debug("Hello from NewComponent! Preparing component...")
        pass

    def set_input_values(self, input_data: InputDataModel) -> None:
        """
        Set the input values for the new component
        """
        pass

    def calculate_a_result(self) -> tuple[float, DataUnits]:
        """
        Example calculation function for the new component
        """
        # Example calculation logic using the input data stored in the component
        logger.debug("Calculating a_result in NewComponent...")
        return 42, DataUnits.DEGREECELSIUS
