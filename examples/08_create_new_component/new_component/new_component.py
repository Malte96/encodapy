from typing import Union

from encodapy.components.basic_component import BasicComponent
from encodapy.config.models import ControllerComponentModel


class NewComponent(BasicComponent):
    """
    Class for a new component
    """

    def __init__(
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
    ) -> None:
        # Add the necessary instance variables here (you need to store the input data in the component)
        # example: self.variable: Optional[float]

        super().__init__(config=config, component_id=component_id)

        # Component-specific initialization logic
