"""
Basic configuration for the components in the EnCoCaPy framework.
Author: Martin Altenburger
"""
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from pandas import DataFrame
from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator

from encodapy.utils.units import DataUnits

# Models to hold the data
class DataPointGeneral(BaseModel):
    """
    Model for datapoints of the controller component.
    
    Contains:
        value: The value of the datapoint, which can be of various types \
            (string, float, int, boolean, dictionary, list, DataFrame, or None)
        unit: Optional unit of the datapoint, if applicable
        time: Optional timestamp of the datapoint, if applicable
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    value: Any
    unit: Optional[DataUnits] = None
    time: Optional[datetime] = None

class DataPointNumber(DataPointGeneral):
    """
    Model for datapoints of the controller component.
    
    Contains:
        value: The value of the datapoint, which is a number (float, int)
        unit: Optional unit of the datapoint, if applicable
        time: Optional timestamp of the datapoint, if applicable
    """

class DataPointString(DataPointGeneral):
    """
    Model for datapoints of the controller component.

    Contains:
        value: The value of the datapoint, which is a string
        unit: Optional unit of the datapoint, if applicable
        time: Optional timestamp of the datapoint, if applicable
    """

    value: str
class DataPointDict(DataPointGeneral):
    """
    Model for datapoints of the controller component.

    Contains:
        value: The value of the datapoint, which is a dictionary
        unit: Optional unit of the datapoint, if applicable
        time: Optional timestamp of the datapoint, if applicable
    """

    value: dict

# Models for the Input Configuration
class IOAllocationModel(BaseModel):
    """
    Model for the input or output allocation.

    Contains:
        `entity`: ID of the entity to which the input or output is allocated
        `attribute`: ID of the attribute to which the input or output is allocated
        `default`: Default value for the input or output
        `unit`: Unit of the input or output
    """

    entity: str = Field(
        ..., description="ID of the entity to which the input or output is allocated"
    )
    attribute: str = Field(
        ..., description="ID of the attribute to which the input or output is allocated"
    )
    default: Optional[Any] = Field(
        None, description="Default value for the input or output"
    )
    unit: Optional[DataUnits] = Field(None, description="Unit of the input or output")


class IOModell((RootModel[Dict[str, IOAllocationModel]])):  # pylint: disable=too-few-public-methods
    """
    Model for the input, staticdata and output of a component.

    It contains a dictionary with the key as the ID of the input, output or static data
    and the value as the allocation model.

    There is no validation for this.
    It is used to create the the ComponentIOModel for each component.
    """
class ConfigDataPoints((RootModel[Dict[str, IOAllocationModel | DataPointGeneral]])):  # pylint: disable=too-few-public-methods
    """
    Model for the configuration of config data points.
    """

class ControllerComponentModel(BaseModel):
    """
    Model for the configuration of the controller components.
    Contains:
    - active: Whether the component is active or not
    - id: The id of the component
    - type: The type of the component (e.g. thermal storage, heat pump, etc. / \
        needs to be defined for individual components)
    - inputs: The inputs of the component as a dictionary with IOAllocationModel \
        for the individual inputs
    - outputs: The outputs of the component as a dictionary with IOAllocationModel \
        for the individual outputs
    - config: The configuration of the component as a dictionary with IOAllocationModel \
          for the individual static data or DataPointModel with direct values
    """

    active: Optional[bool] = True
    id: str
    type: str
    inputs: IOModell
    outputs: IOModell
    config: Optional[ConfigDataPoints] = None

# Models for the internal input and output connections, needs to filled for the components
class OutputData(BaseModel):
    """
    Basemodel for the configuration of the outputs of a component

    Needs to be implemented by the user.
    """

class InputData(BaseModel):
    """
    Basemodel for the configuration of the inputs of a component
    """
    #TODO remove this validator
    # @model_validator(mode="after")
    # def check_default_values(self) -> "InputModel":
    #     """
    #     Check the default_values
    #     """
    #     for name, field in self.model_fields.items():
    #         value = getattr(self, name)
    #         extra = field.json_schema_extra or {}

    #         if isinstance(value, IOAllocationModel) and isinstance(extra, dict):
    #             if "default" in extra and value.default is None:
    #                 value.default = extra["default"]
    #             if "unit" in extra and value.unit is None:
    #                 value.unit = DataUnits(extra["unit"])

    #     return self
class ConfigData(BaseModel):
    """
    Basemodel for the configuration data of a component
    """


class ComponentIOModel(BaseModel):
    """
    Model for the input and output of the thermal storage service.

    Contains:
        `input`: InputModel = Input configuration for the thermal storage service
        `output`: OutputModel = Output configuration for the thermal storage service
    """

    input: InputData = Field(
        ..., description="Input configuration for the thermal storage service"
    )
    output: OutputData = Field(
        ...,
        description="Output configuration for the thermal storage service")

# Custom Exceptions
class ComponentValidationError(Exception):
    """Custom error for invalid configurations."""
