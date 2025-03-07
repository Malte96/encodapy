"""
Description: This file contains the models for the use in the system controller itself.
Authors: Martin Altenburger
TODO: Is it possible to use the models from the configuration also for the system controller?\
    Or could we use less modells?
"""

from datetime import datetime
from typing import Dict, List, Optional, Union
from pandas import DataFrame
from pydantic import BaseModel, ConfigDict
from encodapy.config.models import AttributeModel, CommandModel
from encodapy.config.types import AttributeTypes
from encodapy.utils.units import DataUnits

class InputDataAttributeModel(BaseModel):
    """
    Model for a attribute of input data of the system controller.

    Contains:
    - id: The id of the input data attribute
    - data: The input data as a DataFrame or a single value
    - unit: The unit of the input data
    - data_type: The type of the input data (AttributeTypes)
    - data_available: If the data is available
    - latest_timestamp_input: The latest timestamp of the input data from the query or None,\
        if the data is not available
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    data: Union[str, float, int, bool, Dict, List, DataFrame, None]
    unit: Union[DataUnits, None] = None
    data_type: AttributeTypes
    data_available: bool
    latest_timestamp_input: Union[datetime, None]


class InputDataEntityModel(BaseModel):
    """
    Model for the input data of the system controller.

    Contains:
    - id: The id of the input data entity
    - attributes: List of the input data attributes as InputDataAttributeModel
    """

    id: str
    attributes: List[InputDataAttributeModel]


class StaticDataEntityModel(InputDataEntityModel):
    """
    Model for the static data of the system controller, same like InputDataEntityModel.

    Contains:
    - id: The id of the input data entity
    - attributes: List of the input data attributes as InputDataAttributeModel
    """


class OutputDataAttributeModel(BaseModel):
    """
    Model for a attribute of output data of the system controller - status based on the status\
        of the interface.

    Contains:
    - id: The id of the output data attribute
    - latest_timestamp_output: The latest timestamp of the output data from the query or None,\
        if the data is not available
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    latest_timestamp_output: Optional[Union[datetime, None]] = None


class OutputDataEntityModel(BaseModel):
    """
    Model for the status of the output data of the system controller.

    Contains:
    - id: The id of the output entity
    - latest_timestamp_output: The latest timestamp of the output data from the query or None,\
        if the data is not available

    - attributes: List of the output data attributes as OutputDataAttributeModel
    - commands: List of the output data commands as OutputDataCommandModel

    """

    id: str
    attributes: Optional[List[AttributeModel]] = []
    attributes_status: Optional[List[OutputDataAttributeModel]] = []
    commands: Optional[List[CommandModel]] = []


class InputDataModel(BaseModel):
    """
    Model for the input data of the system controller.

    Contains:
    - input_entitys: List of the input data entitys as InputDataEntityModel
    - output_entitys: List of the output data entitys as OutputDataEntityModel
    - context_entitys: List of the context data entitys as InputDataEntityModel\
        (a extra ContextDataEntityModel is not nessesary, may be in future?)
    """

    input_entities: list[InputDataEntityModel]
    output_entities: list[OutputDataEntityModel]
    static_entities: list[StaticDataEntityModel]


# class ContextDataModel(BaseModel):
#     """
#     Model for the context data of the system controller.

#     Contains:
#     - input_entitys: List of the context data entitys as ContexttDataEntityModel

#     """

#     context_entities: list[InputDataEntityModel]


class OutputDataModel(BaseModel):
    """
    Model for the output data of the system controller.

    Contains:
    - output_entitys: List of the output data entitys as OutputDataEntityModel
    """

    entities: list[OutputDataEntityModel]


class ComponentModel(BaseModel):
    """
    Model for the dataflow (input/output) of the controller.

    Contains:
    - entity: The entity (input / output) of the datapoint for the controller
    - attribute: The attribute of the datapoint for the controller
    """

    entity_id: str
    attribute_id: str


class DataTransferComponentModel(ComponentModel):
    """
    Model for the components of the data transfer between calculation and the basic service.

    Contains:
    - entity_id: The id of the entity of the component
    - attribute_id: The id of the attribute of the component
    - value: The output data value as OutputDataModel
    - unit: The unit of the output data
    - timestamp: The timestamp of the output
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    value: Union[str, float, int, bool, Dict, List, DataFrame, None]
    unit: Union[DataUnits, None] = None
    timestamp: Optional[Union[datetime, None]] = None


class DataTransferModel(BaseModel):
    """
    Model for the data transfer between calculation and the basic service.

    Contains:
    - components: List of the components of the data transfer as DataTransferComponentModel
    """

    components: list[DataTransferComponentModel] = []


class MetaDataModel(BaseModel):
    """
    Model for the metadata of datapoints of the controller.

    Contains:
    - timestamp: The timestamp of the data
    - unit: The unit of the data
    """

    timestamp: Union[datetime, None] = None
    unit: Union[DataUnits, None] = None
