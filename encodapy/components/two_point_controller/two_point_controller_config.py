"""
Description: Configuration model for the two-point controller component.
Author: Martin Altenburger
"""

from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field

from encodapy.components.basic_component_config import (
    InputModel,
    IOAllocationModel,
    OutputModel,
)
from encodapy.utils.units import DataUnits


class TwoPointControllerInputModel(InputModel):
    """
    Model for the input of the two-point controller component.
    
    Contains:
        current_value (IOAllocationModel): The current value of the input.
        latest_control_signal (IOAllocationModel): The latest control signal output \
            from the two-point controller.
    """

    current_value: IOAllocationModel = Field(
        ..., description="Current value of the input, typically a sensor reading"
    )
    latest_control_signal: IOAllocationModel = Field(
        ..., description="Latest control signal output from the two-point controller"
    )


class TwoPointControllerOutputModel(OutputModel):
    """
    Model for the output of the two-point controller component.

    Contains:
        control_signal (IOAllocationModel): The control signal output from the two-point controller.
    """

    control_signal: IOAllocationModel = Field(
        ...,
        description="Control signal output from the two-point controller",
        json_schema_extra={"calculation": "get_control_signal"},
    )


class TwoPointControllerStaticData(Enum):
    """
    Enum class that defines the static data keys for the two-point controller.
    """

    HYSTERESIS = "hysteresis"
    SETPOINT = "setpoint_value"
    COMMAND_ENABLED = "command_enabled"
    COMMAND_DISABLED = "command_disabled"


class TwoPointControllerValues(BaseModel):
    """
    Model for the values of the two-point controller component.

    Contains:
        current_value (float): The current value of the controlled variable.
        current_unit (Optional[DataUnits]): The unit of the current value.
        latest_control_signal (Union[str, float, int, bool]): The latest control signal output.
    """

    current_value: float
    current_unit: Optional[DataUnits] = None
    latest_control_signal: Union[str, float, int, bool]
