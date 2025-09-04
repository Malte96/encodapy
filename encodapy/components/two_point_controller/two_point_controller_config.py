"""
Description: Configuration model for the two-point controller component.
Author: Martin Altenburger
"""

from typing import Optional, Union

from pydantic import BaseModel, Field

from encodapy.components.basic_component_config import (
    DataPointGeneral,
    DataPointNumber,
    InputData,
    OutputData,
    ConfigData,
)
from encodapy.utils.units import DataUnits


class TwoPointControllerInputData(InputData):
    """
    Model for the input of the two-point controller component.
    
    Contains:
        current_value (DataPointNumber): The current value of the input.
        latest_control_signal (DataPointNumber): The latest control signal output \
            from the two-point controller.
    """

    current_value: DataPointNumber = Field(
        ..., description="Current value of the input, typically a sensor reading"
    )
    latest_control_signal: DataPointNumber = Field(
        ..., description="Latest control signal output from the two-point controller"
    )


class TwoPointControllerOutputData(OutputData):
    """
    Model for the output of the two-point controller component.

    Contains:
        control_signal (DataPointNumber): The control signal output from the two-point controller.
    """

    control_signal: DataPointNumber = Field(
        ...,
        description="Control signal output from the two-point controller",
        json_schema_extra={"calculation": "get_control_signal"},
    )

class TwoPointControllerConfigData(ConfigData):
    """
    Model for the configuration data of the thermal storage service.
    """
    hysteresis: DataPointNumber = Field(
        ...,
        description="Hysteresis value for the two-point controller",
    )
    setpoint: DataPointNumber = Field(
        ...,
        description="Setpoint value for the two-point controller",
    )
    command_enabled: DataPointGeneral = Field(
        ...,
        description="Value representing the enabled state of the control signal",
    )
    command_disabled: DataPointGeneral = Field(
        ...,
        description="Value representing the disabled state of the control signal",
    )

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
