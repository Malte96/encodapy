# Description: This file contains the models for the use in the system controller itself.
# Authors: Martin Altenburger

from pydantic import BaseModel, ConfigDict
from pandas import DataFrame
from datetime import datetime
from typing import Union, Optional, List, Dict
from controller_software.config.types import AttributeTypes

class InputDataAttributeModel(BaseModel):
    """
    Model for a attribute of input data of the system controller.
    
    Contains:
    - id: The id of the input data attribute
    - data: The input data as a DataFrame or a single value
    - data_available: If the data is available
    - latest_timestamp_input: The latest timestamp of the input data from the query or None, if the data is not available
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id:str
    data: Union[str, float, int, bool, Dict, List, DataFrame, None]
    data_type: AttributeTypes
    data_available: bool
    latest_timestamp_input: Union[datetime, None]
    
class InputDataEntityModel(BaseModel):
    """
    Model for the input data of the system controller.
    
    Contains:
    - id: The id of the input data entity
    - data: The input data as a DataFrame or a single value
    - data_available: If the data is available
    - latest_timestamp_input: The latest timestamp of the input data from the query or None, if the data is not available
    """
    id: str
    attributes: List[InputDataAttributeModel]
 
class OutputDataAttributeModel(BaseModel):
    """
    Model for a attribute of output data of the system controller.
    
    Contains:
    - id: The id of the output data attribute
    - latest_timestamp_output: The latest timestamp of the output data from the query or None, if the data is not available
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str
    latest_timestamp_output: Optional[Union[datetime, None]] = None 
    value: Optional[Union[str, float, int, bool, Dict, List, DataFrame, None]] = None
    timestamp: Optional[Union[datetime, None]] = None
    
       
class OutputDataCommandModel(BaseModel):
    """
    Model for a command in the output data of the system controller.
    
    Contains:
    - id: The id of the output command
    - value: The value of the command / output data
    """
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    
    id: str
    value: Union[str, float, int, bool, Dict, List, DataFrame, None]


class OutputDataEntityModel(BaseModel):
    """
    Model for the status of the output data of the system controller.
    
    Contains:
    - id: The id of the output entity
    - latest_timestamp_output: The latest timestamp of the output data from the query or None, if the data is not available
    
    - attributes: List of the output data attributes as OutputDataAttributeModel
    - commands: List of the output data commands as OutputDataCommandModel
    
    """
    id:str
    attributes: Optional[List[OutputDataAttributeModel]] = []
    commands: Optional[List[OutputDataCommandModel]] = []
    

class InputDataModel(BaseModel):
    """
    Model for the input data of the system controller.
    
    Contains:
    - input_entitys: List of the input data entitys as InputDataEntityModel
    - output_entitys: List of the output data entitys as OutputDataEntityModel
    """
    
    input_entities: list[InputDataEntityModel]
    output_entities: list[OutputDataEntityModel]
    
class OutputDataModel(BaseModel):
    
    """
    Model for the output data of the system controller.
    
    Contains:
    - output_entitys: List of the output data entitys as OutputDataEntityModel
    """
    
    entities: list[OutputDataEntityModel]