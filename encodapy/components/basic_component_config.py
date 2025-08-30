"""
Basic configuration for the components in the EnCoCaPy framework.
Author: Martin Altenburger
"""

from typing import Any, Dict, List, Optional, Union

from pandas import DataFrame
from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator

from encodapy.utils.units import DataUnits


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
    - staticdata: The static data of the component as a dictionary with IOAllocationModel \
        for the individual static data
    - config: The configuration of the component as a dictionary
    
    """

    active: Optional[bool] = True
    id: str
    type: str
    inputs: IOModell
    outputs: IOModell
    staticdata: Optional[IOModell] = None
    config: Optional[dict] = None


class DataPointModel(BaseModel):
    """
    Model for the static data attributes of the controller component.
    
    Contains:
        value: The value of the static data attribute, which can be of various types \
            (string, float, int, boolean, dictionary, list, DataFrame, or None)
        unit: Optional unit of the static data attribute, if applicable
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    value: Union[str, float, int, bool, dict, List, DataFrame, None]
    unit: Optional[DataUnits] = None


class ControllerComponentStaticData(  # pylint: disable=too-few-public-methods
    RootModel[Dict[str, DataPointModel]]
):
    """
    Model for the static data of the controller.
    
    Contains:
        - root: The static data as a dictionary with the key as the ID of the static data \
            (like in the config) and the value as the value of the static data.
    """


# Custom Exceptions
class ComponentValidationError(Exception):
    """Custom error for invalid configurations."""


# Models for the internal input and output connections, needs to filled for the components


class OutputModel(BaseModel):
    """
    Basemodel for the configuration of the outputs of a component

    Needs to be implemented by the user.
    """


class InputModel(BaseModel):
    """
    Basemodel for the configuration of the inputs of a component
    """

    @model_validator(mode="after")
    def check_default_values(self) -> "InputModel":
        """
        Check the default_values
        """
        for name, field in self.model_fields.items():
            value = getattr(self, name)
            extra = field.json_schema_extra or {}

            if isinstance(value, IOAllocationModel) and isinstance(extra, dict):
                if "default" in extra and value.default is None:
                    value.default = extra["default"]
                if "unit" in extra and value.unit is None:
                    value.unit = DataUnits(extra["unit"])

        return self


class ComponentIOModel(BaseModel):
    """
    Model for the input and output of the thermal storage service.

    Contains:
        `input`: InputModel = Input configuration for the thermal storage service
        `output`: OutputModel = Output configuration for the thermal storage service
    """

    input: InputModel = Field(
        ..., description="Input configuration for the thermal storage service"
    )
    output: OutputModel = Field(
        ..., description="Output configuration for the thermal storage service"
    )
