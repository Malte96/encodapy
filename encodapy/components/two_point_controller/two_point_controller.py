"""
Description: Simple component of a two-point controller
Author: Martin Altenburger
"""

from typing import Optional, Union
from loguru import logger
from encodapy.components.basic_component import BasicComponent
from encodapy.components.basic_component_config import ControllerComponentModel
from encodapy.components.two_point_controller.two_point_controller_config import (
    TwoPointControllerConfigData,
    TwoPointControllerInputData,
    TwoPointControllerOutputData,
)
from encodapy.utils.models import (
    StaticDataEntityModel,
)
from encodapy.utils.datapoints import DataPointGeneral


class TwoPointController(BasicComponent):
    """
    Class for a two-point controller
    Args:
        config (Union[ControllerComponentModel, list[ControllerComponentModel]]): \
            The configuration for the controller.
        component_id (str): The unique identifier for the component.
        static_data (Optional[list[StaticDataEntityModel]]): Static data for the component.
    """

    def __init__(
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
        static_data: Optional[list[StaticDataEntityModel]] = None,
    ):
        self.config_data: TwoPointControllerConfigData
        self.input_data: TwoPointControllerInputData
        self.output_data: TwoPointControllerOutputData

        super().__init__(
            component_id=component_id, config=config, static_data=static_data
        )

    def get_control_signal(
        self,
    ) -> DataPointGeneral:
        """Calculate the control signal based on current and setpoint values."""

        minimal_value = (
            self.config_data.setpoint.value - self.config_data.hysteresis.value
        )

        # Raise errors if units do not match
        try:
            assert self.config_data.hysteresis.unit == self.config_data.setpoint.unit, (
                f"Units of hysteresis ({self.config_data.hysteresis.unit}) "
                f"and setpoint ({self.config_data.setpoint.unit}) must be the same!"
            )
            assert (
                self.input_data.current_value.unit == self.config_data.setpoint.unit
            ), (
                f"Units of current_value ({self.input_data.current_value.unit}) "
                f"and setpoint ({self.config_data.setpoint.unit}) must be the same!"
            )
            assert (
                self.input_data.latest_control_signal.unit
                == self.config_data.command_enabled.unit
            ), (
                f"Units of latest_control_signal ({self.input_data.latest_control_signal.unit}) "
                f"and command_enabled ({self.config_data.command_enabled.unit}) must be the same!"
            )
            assert (
                self.input_data.latest_control_signal.unit
                == self.config_data.command_disabled.unit
            ), (
                f"Units of latest_control_signal ({self.input_data.latest_control_signal.unit}) "
                f"and command_disabled ({self.config_data.command_disabled.unit}) must be the same!"
            )
        except AssertionError as e:
            logger.error(f"Unit assertion error in {self.component_config.id}: {e}")
            raise

        if self.input_data.current_value.value < minimal_value:
            return DataPointGeneral(
                value=self.config_data.command_enabled.value,
                unit=self.config_data.command_enabled.unit,
            )

        if self.input_data.current_value.value > float(self.config_data.setpoint.value):
            return DataPointGeneral(
                value=self.config_data.command_disabled.value,
                unit=self.config_data.command_disabled.unit,
            )

        if (
            self.input_data.latest_control_signal.value
            == self.config_data.command_enabled.value
            and self.input_data.current_value.value > minimal_value
        ):
            return DataPointGeneral(
                value=self.config_data.command_enabled.value,
                unit=self.config_data.command_enabled.unit,
            )

        return DataPointGeneral(
            value=self.config_data.command_disabled.value,
            unit=self.config_data.command_disabled.unit,
        )

    def calculate(self):
        """
        Calculate the output data based on the input data and configuration.
        """

        self.output_data = TwoPointControllerOutputData(
            control_signal=self.get_control_signal()
        )
