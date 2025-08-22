"""
Description: Simple component of a two-point controller
Author: Martin Altenburger
"""
from typing import Dict, List, Union, cast, Optional
from pydantic import ValidationError
from loguru import logger
from pandas import DataFrame
from encodapy.components.basic_component import BasicComponent
from encodapy.components.components_basic_config import(
    ControllerComponentModel
)
from encodapy.utils.models import InputDataEntityModel, StaticDataEntityModel
from encodapy.utils.units import DataUnits
from encodapy.components.two_point_controller.two_point_controller_config import (
    TwoPointControllerValues
)


class TwoPointController(BasicComponent):
    """
    Class for a two-point controller
    Args:
        config (Union[ControllerComponentModel, list[ControllerComponentModel]]): \
            The configuration for the controller.
        component_id (str): The unique identifier for the component.
        static_data (Optional[list[StaticDataEntityModel]]): Static data for the component.
    """

    def __init__(self,
                 config:Union[ControllerComponentModel, list[ControllerComponentModel]],
                 component_id:str,
                 static_data: Optional[list[StaticDataEntityModel]] = None
                 ):

        self.controller_values: Optional[TwoPointControllerValues] = None
        self.unit_hysteresis: Optional[DataUnits] = None

        super().__init__(component_id=component_id,
                         config=config,
                         static_data=static_data)


    def prepare_component(self):
        _, hysteresis_unit = self.get_component_static_data(component_id="hysteresis")

        if hysteresis_unit is not None:
            self.unit_hysteresis = hysteresis_unit

    def set_input_values(self, input_entities: list[InputDataEntityModel]) -> None:


        if self.io_model is None:
            logger.error("IO model is not set.")
            return

        sensor_values: dict[str, Union[bool, float, None]] = {}
        sensor_units: dict[str, Optional[DataUnits]] = {}

        for key, datapoint_information in self.io_model.input.__dict__.items():

            if datapoint_information is None:
                continue

            value, unit = self.get_component_input(
                    input_entities=input_entities,
                    input_config=datapoint_information
                )

            if value is not None and not isinstance(value, (str, int, float, bool)):
                logger.error(f"Invalid value for '{key}: {value}' "
                             "Sensor Values are not set correctly")
                return

            if value is None or isinstance(value, bool):
                sensor_values[key] = value
            else:
                sensor_values[key] = float(value)

            sensor_units[key] = unit

        latest_control_signal_raw = sensor_values.get("latest_control_signal")

        if latest_control_signal_raw is None:
            command_disabled, _command_disabled_unit = self.get_component_static_data(
                component_id="command_disabled")

            if not isinstance(command_disabled, (str, int, float)):
                error_msg = "Latest control signal is not set and command_disabled \
                    is not a valid value."
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.warning("Latest control signal is not set. "
                           f" Using default {command_disabled}.")
            latest_control_signal = command_disabled
        else:
            latest_control_signal = latest_control_signal_raw

        try:
            controller_values = TwoPointControllerValues(
                current_value=cast(float, sensor_values.get("current_value")),
                current_unit=sensor_units.get("current_value"),
                latest_control_signal=cast(Union[str, float, int, bool], latest_control_signal)
            )
        except (ValidationError, KeyError) as e:
            logger.error(f"Error setting controller values: {e}")
            return

        self.controller_values = controller_values

    def get_control_signal(self
                           ) -> tuple[
                               Union[str, float, int, bool, Dict, List, DataFrame, None],
                               Optional[DataUnits]
                               ]:
        """Calculate the control signal based on current and setpoint values."""
        if self.controller_values is None:
            logger.error("Controller values are not set.")
            raise ValueError("Controller values are not set.")
        if self.unit_hysteresis is None:
            logger.error("Hysteresis unit is not set.")
            raise ValueError("Hysteresis unit is not set.")

        setpoint, _ = self.get_component_static_data(
            component_id="setpoint_value",
            unit=self.controller_values.current_unit)
        hysteresis, _ = self.get_component_static_data(
            component_id="hysteresis",
            unit=self.unit_hysteresis)
        command_enabled, command_enabled_unit = self.get_component_static_data(
            component_id="command_enabled")
        command_disabled, command_disabled_unit = self.get_component_static_data(
            component_id="command_disabled")

        if setpoint is None or hysteresis is None \
            or command_enabled is None or command_disabled is None:
            logger.error("One or more static data values are not set.")
            raise ValueError("One or more static data values are not set.")


        if not isinstance(setpoint, (float, int, str)) \
            or not isinstance(hysteresis, (float, int, str)):
            logger.error("Setpoint or hysteresis is not a valid number.")
            raise ValueError("Setpoint or hysteresis is not a valid number.")

        minimal_value = (
            float(setpoint) - float(hysteresis)
        )
        #TODO how to handle the units here?

        if self.controller_values.current_value < minimal_value:
            return command_enabled, command_enabled_unit

        if self.controller_values.current_value > float(setpoint):
            return command_disabled, command_disabled_unit

        if (
            self.controller_values.latest_control_signal == command_enabled
            and self.controller_values.current_value > minimal_value
        ):
            return command_enabled, command_enabled_unit

        return command_disabled, command_disabled_unit
