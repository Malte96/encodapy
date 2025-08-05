"""
This module provides basic components for the encodapy package.
"""
# from loguru import logger
from typing import Union
from encodapy.config.models import ControllerComponentModel, StaticDataModel
from encodapy.utils.models import InputDataEntityModel
from encodapy.components.components_basic_config import IOAllocationModel

class BasicComponent:
    """
    Base class for all components in the encodapy package.
    This class provides basic functionality that can be extended by specific components.
    
    Contains methods for:
    - Getting component configuration: `get_component_config()`
    - Getting input values: `get_input_values()`
    """
    def __init__(self,
                 config: Union[ControllerComponentModel, StaticDataModel, list[ControllerComponentModel]],
                 component_id:str
                 ) -> None:
        if isinstance(config, ControllerComponentModel):
            self.component_config = ControllerComponentModel.model_validate(config)
        else:
            self.component_config = ControllerComponentModel.model_validate(
                self.get_component_config(
                    config = config,
                    component_id = component_id
                )
            )


    def get_component_config(self,
                              config: list[ControllerComponentModel],
                              component_id:str
                              )-> ControllerComponentModel:
        """
        Function to get the configuration of a specific component from the service configuration
        Args:
            component_names (str): Name of the component to get the configuration
        Returns:
            ControllerComponentModel: Configuration of the component by name
        
        Raises:
            ValueError: If the component with the given ID is not found in the configuration
        """
        for component in config:
            if component.id == component_id:
                return component
            raise ValueError("No thermal storage configuration found")

    def get_input_values(self,
                         input_entities:list[InputDataEntityModel],
                         input_config:IOAllocationModel,
                         )-> Union[float, int, str, bool]:
        """
        Function to get the values of the input data for a spesific input configuration \
            of a component of the controller (or a inividual one).

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
