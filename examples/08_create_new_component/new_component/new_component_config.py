"""
Defines the configuration data models for the new component.
"""

from typing import Optional

from pydantic import Field

from encodapy.components.basic_component_config import (
    ConfigData,
    InputData,
    OutputData,
)
from encodapy.utils.datapoints import DataPointGeneral, DataPointNumber


class NewComponentInputData(InputData):
    """
    Input model for the new component
    """

    a_general_input: DataPointGeneral = Field(
        ...,
        description="A general input of the new component",
        json_schema_extra={"default": "Hello new component!"},
    )
    a_number_input: DataPointNumber = Field(
        DataPointNumber(value=30),
        description="A number input of the new component",
        json_schema_extra={"unit": "CEL"},
    )
    another_number_input: DataPointNumber = Field(
        DataPointNumber(value=10),
        description="Another number input of the new component",
        json_schema_extra={"unit": "KEL"},
    )


class NewComponentOutputData(OutputData):
    """
    Output model for the new component
    """

    result: DataPointGeneral = Field(
        ...,
        description="Result of the new component",
        json_schema_extra={"unit": "CEL"},
    )
    optional_result: Optional[DataPointGeneral] = Field(
        ...,
        description="This is an optional result of the new component and does not need to be exported.",
        json_schema_extra={"unit": "CEL"},
    )


class NewComponentConfigData(ConfigData):
    """
    Config data model for the new component
    """

    config_value: DataPointGeneral = Field(
        ...,
        description="Static value for the new component",
    )
    optional_config_value: Optional[DataPointGeneral] = Field(
        DataPointGeneral(value=1),
        description="Optional static value for the new component",
    )
