# from enum import Enum
from typing import Optional

from pydantic import Field

from encodapy.components.basic_component_config import (
    ConfigData,
    DataPointGeneral,
    DataPointNumber,
    InputData,
    OutputData,
)


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
    optional_input: Optional[DataPointGeneral] = Field(
        None,
        description="Optional input of the new component",
        json_schema_extra={"default": "10", "unit": "CEL"},
    )


class NewComponentOutputData(OutputData):
    """
    Output model for the new component
    """

    a_result: DataPointGeneral = Field(
        ...,
        description="Result of the new component",
        json_schema_extra={"unit": "CEL"},
    )
    # optional_result: Optional[DataPointGeneral] = Field(
    #     ...,
    #     description="This is an optional result of the new component and does not need to be exported.",
    #     json_schema_extra={"unit": "$unit_value"},
    # )
    # TODO: SERVICE STOPS RUNNING: Needs to throw error if no matching calculation function is defined
    # b_result: IOAllocationModel = Field(
    #     ...,
    #     description="Test no definition of calculation function",
    #     json_schema_extra={"calculation": "calculate_b_result"},
    # )


# TODO: Throws errors due only an empty list in config
# TODO: staticdata should be optional, but is required in config, otherwise validation error
# class NewComponentStaticData(Enum):
#     """
#     Static data for the new component (Optional)
#     """

#     A_STATIC_VALUE = "setpoint for something"


class NewComponentConfigData(ConfigData):
    """
    Config data model for the new component
    """

    a_config_value: DataPointNumber = Field(
        ...,
        description="Static value for the new component",
        json_schema_extra={"default": 5, "unit": "KEL"},
    )
    optional_config_value: Optional[DataPointGeneral] = Field(
        DataPointGeneral(value=1),
        description="Optional static value for the new component",
    )
