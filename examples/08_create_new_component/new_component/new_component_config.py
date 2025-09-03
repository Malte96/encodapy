# from enum import Enum
from typing import Optional

from pydantic import Field

from encodapy.components.basic_component_config import (
    InputModel,
    IOAllocationModel,
    OutputModel,
)


class NewComponentInputModel(InputModel):
    """
    Input model for the new component
    """

    a_input: IOAllocationModel = Field(
        ...,
        description="Input of the new component",
        json_schema_extra={"default": "20", "unit": "CEL"},
    )

    another_input: IOAllocationModel = Field(
        ...,
        description="Another input of the new component",
        json_schema_extra={"default": "30", "unit": "CEL"},
    )

    optional_input: Optional[IOAllocationModel] = Field(
        None,
        description="Optional input of the new component",
        json_schema_extra={"default": "10", "unit": "CEL"},
    )


class NewComponentOutputModel(OutputModel):
    """
    Output model for the new component
    """

    a_result: IOAllocationModel = Field(
        ...,
        description="Result of the new component",
        json_schema_extra={"calculation": "calculate_a_result"},
    )

    another_result: IOAllocationModel = Field(
        ...,
        description="Another result of the new component",
        json_schema_extra={"calculation": "calculate_another_result"},
    )

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
