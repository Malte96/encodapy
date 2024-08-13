# Description: This file contains the models for the configuration of the system controller.
# Authors: Martin Altenburger

from pydantic import BaseModel, ValidationError
import json
from typing import Union
from controller_software.config.types import Interfaces, AttributeTypes, ControllerComponents

# TODO: Add the configuration parameters and the import from a json-file
# TODO: Add a documentation for the models
# TODO: Is this validation implementation useful and correct?



class InterfaceModel(BaseModel):
    """Base class for the interfaces"""
    
    mqtt: bool
    fiware: bool
    file: dict


    
class AttributeModel(BaseModel):
    """Base class for the attributes"""
    
    id: str
    id_interface: str
    type: AttributeTypes
    value: Union[str, None] = None
    
class InputModel(BaseModel):
    """
    Model for the configuration of inputs.
    
    Contains:
    - id: The id of the input
    - interface: The interface of the input
    - id_interface: The id of the input on the interface
    - attributes: The attributes of the

    """
    id: str
    interface: Interfaces
    id_interface: str
    attributes: list[AttributeModel]
    
class OutputModel(BaseModel):
    """
    Model for the configuration of outputs.
    
    Contains:
    - id: The id of the output
    - interface: The interface of the output
    - id_interface: The id of the output on the interface
    - attributes: The attributes of the output
    """
    id: str
    interface: Interfaces
    id_interface: str
    attributes: list[AttributeModel]
    
class ControllerComponentModel(BaseModel):
    """
    Model for the configuration of the controller components.
    """
    
    id: str
    type: ControllerComponents          # TODO: How to reference the component types?
    inputs: list[str]                   # TODO: How to reference the input/output models?
    outputs: list[str]
    

class ConfigModel(BaseModel):
    """
    Base Model for the configuration
    
    Contains:
    - interfaces: The interfaces of the system controller
    - inputs: The inputs of the system controller
    - outputs: The outputs of the system controller
    - metadata: The metadata for devices the system controller #TODO: Is this needed? Import on other places?
    - controller_components: The components of the controller
    - controller_settings: The settings for the controller #TODO: What is needed here?
    """
    
    interfaces: InterfaceModel
       
    inputs: list[InputModel]
    outputs: list[OutputModel]
    metadata: list

    controller_components: list[ControllerComponentModel]
    
    controller_settings: dict
    
    
    @classmethod
    def from_json(cls, file_path: str):
        """
        Load the configuration from a JSON file.
        """
        try:
            with open(file_path, 'r') as f:
                config_data = json.load(f)
            return cls(**config_data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Couldn't load configuration from json file: {e}")
        except ValidationError as e:
            raise KeyError(f"Error during validation: {e}")