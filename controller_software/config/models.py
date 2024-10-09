# Description: This file contains the models for the configuration of the system controller.
# Authors: Martin Altenburger

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from controller_software.config.types import (AttributeTypes,
                                              ControllerComponents, Interfaces,
                                              TimerangeTypes)
from controller_software.utils.error_handling import ConfigError
from controller_software.utils.units import DataUnits, TimeUnits
from filip.models.base import DataType
from loguru import logger
from pandas import DataFrame
from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic.functional_validators import model_validator

# TODO: Add the configuration parameters and the import from a json-file
# TODO: Add a documentation for the models
# TODO: Is this validation implementation useful and correct?


class InterfaceModel(BaseModel):
    """Base class for the interfaces
    TODO: - How to use this model?
    """

    mqtt: bool = False
    fiware: bool = False
    file: bool = False


class AttributeModel(BaseModel):
    """
    Base class for the attributes

    Contains:
    - id: The id of the attribute
    - id_interface: The id of the attribute on the interface (if not set, the id is used)
    - type: The type of the attribute
    - value: The value of the attribute
    - unit: The unit of the attribute
    - datatype: The datatype of the attribute
    - timestamp: The timestamp of the attribute

    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    id_interface: str = id
    type: AttributeTypes = AttributeTypes.VALUE
    value: Union[str, float, int, bool, Dict, List, DataFrame, None] = None
    unit: Union[DataUnits, None] = None
    datatype: DataType = DataType.NUMBER
    timestamp: Union[datetime, None] = None


class CommandModel(BaseModel):
    """
    Base class for the commands

    Contains:
    - id: The id of the command
    - id_interface: The id of the command on the interface (if not set, the id is used)
    - value: The value of the command
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    id_interface: str = id
    value: Union[str, int, float, List, Dict, None] = None


class InputModel(BaseModel):
    """
    Model for the configuration of inputs.

    Contains:
    - id: The id of the input
    - interface: The interface of the input
    - id_interface: The id of the input on the interface
    - attributes: The attributes of the

    """

    id: str
    interface: Interfaces
    id_interface: str
    attributes: list[AttributeModel]


class OutputModel(BaseModel):
    """
    Model for the configuration of outputs.

    Contains:
    - id: The id of the output
    - interface: The interface of the output
    - id_interface: The id of the output on the interface
    - attributes: The attributes of the output
    """

    id: str
    interface: Interfaces
    id_interface: str
    attributes: list[AttributeModel]
    commands: list[CommandModel]


class ControllerComponentModel(BaseModel):
    """
    Model for the configuration of the controller components.
    TODO: - Improve the model
    """

    active: bool = True
    id: str
    type: ControllerComponents  # TODO: How to reference the component types?
    inputs: dict  # TODO: How to reference the input/output models? Need this also a modell? Would that be better?
    outputs: dict
    config: dict


class TimeSettingsCalculationModel(BaseModel):
    """
    Base class for the calculation time settings of the controller / system.

    Contains:
    - timerange: The timerange for the calculation (if only one value is needed and primary value - otherwise use timerange_min and timerange_max)
    - timerange_min: The minimum timerange for the calculation (only used if timerange is not set and timerange_max is set too)
    - timerange_max: The maximum timerange for the calculation (only used if timerange is not set and timerange_min is set too)
    - timerange_type: Type of time period, relative to the last result or absolute at the current time (if not set, the default type is absolute)
    - timerange_unit: The unit of the timerange (if not set, the default unit is minute)
    - timestep: The timestep for the calculation (if not set, the default value is 1), the related unit is defined in the timestep_unit attribute
    - timestep_unit: The unit of the timestep (if not set, the default unit is second)
    - sampling_time: The sampling time for the calculation (if not set, the default value is 1), the related unit is defined in the sampling_time_unit attribute
    - sampling_time_unit: The unit of the sampling time (if not set, the default unit is minute)
    """

    timerange: Optional[float] = None
    timerange_min: Optional[float] = None
    timerange_max: Optional[float] = None
    timerange_type: Optional[TimerangeTypes] = TimerangeTypes.ABSOLUTE
    timerange_unit: Optional[TimeUnits] = TimeUnits.MINUTE

    timestep: Union[float, int] = 1
    timestep_unit: TimeUnits = TimeUnits.SECOND

    sampling_time: Union[float, int] = 1
    sampling_time_unit: TimeUnits = TimeUnits.MINUTE

    @model_validator(mode="after")
    def check_timerange_parameters(self) -> "TimeSettingsCalculationModel":
        """Check the timerange parameters.

        Raises:
            ValueError: If the timerange parameters are not set correctly

        Returns:
            TimeSettingsCalculationModel: The model with the validated parameters
        """

        if self.timerange is None and (
            self.timerange_min is None or self.timerange_max is None
        ):
            raise ValueError(
                "Either 'timerange' or 'timerange_min' and 'timerange_max' must be set."
            )

        if self.timerange is not None and (
            self.timerange_min is not None or self.timerange_max is not None
        ):
            logger.warning(
                "Either 'timerange' or both 'timerange_min' and 'timerange_max' should be set, not both. Using 'timerange' as the only value."
            )

            self.timerange_min = None
            self.timerange_max = None

        return self

    @model_validator(mode="before")
    @classmethod
    def check_timestep_units(cls, data: Any) -> Any:
        """Checks the units of the times in the configuration and provides feedback (debug logging) if the default values are used

        Args:
            data (Any): The data to check (input data)

        Returns:
            Any: The data with the checked timestep units
        """
        if "timestep" not in data:
            logger.debug("No timestep is set - using default value '1'")
        if "timestep_unit" not in data:
            logger.debug("No timestep unit is set - using default unit 'second'")
        if "sampling_time" not in data:
            logger.debug("No sampling time is set - using default value '1'")
        if "sampling_time_unit" not in data:
            logger.debug("No sampling time unit is set - using default unit 'minute'")
        if "timerange_unit" not in data:
            logger.debug("No timerange unit is set - using default unit 'minute'")
        if "timerange_type" not in data:
            logger.debug("No timerange type is set - using default type 'absolute'")
        return data


class TimeSettingsCalibrationModel(BaseModel):
    """
    Base class for the calibration time settings of the controller / system.

    Contains:
    - sampling_time: The sampling time for the calibration (if not set, the default value is 1), the related unit is defined in the sampling_time_unit attribute
    - sampling_time_unit: The unit of the sampling time (if not set, the default unit is day)

    TODO: Add the needed fields
        - timerange: The timerange for the calibration
    """

    sampling_time: Union[float, int] = 1
    sampling_time_unit: TimeUnits = TimeUnits.DAY


class TimeSettingsResultsModel(BaseModel):

    timestep: Union[float, int] = 1
    timestep_unit: TimeUnits = TimeUnits.SECOND


class TimeSettingsModel(BaseModel):
    """
    Base class for the time settings of the controller / system.

    Contains:
    - calculation: The timeranges and settings für the calculation
    - calibration: The timeranges and settings for the calibration
    - results: The timesettings for the results

    TODO: Add the needed fields - calibration?
    """

    calculation: TimeSettingsCalculationModel
    calibration: Optional[TimeSettingsCalibrationModel] = None
    results: Optional[TimeSettingsResultsModel] = None


class ControllerSettingModel(BaseModel):
    """
    Model for the configuration of the controller settings.

    TODO: What is needed here?
    """

    time_settings: TimeSettingsModel


class ConfigModel(BaseModel):
    """
    Base Model for the configuration

    Contains:
    - interfaces: The interfaces of the system controller
    - inputs: The inputs of the system controller
    - outputs: The outputs of the system controller
    - metadata: The metadata for devices the system controller #TODO: Is this needed? Import on other places?
    - controller_components: The components of the controller
    - controller_settings: The settings for the controller #TODO: What is needed here?
    """

    interfaces: InterfaceModel

    inputs: list[InputModel]
    outputs: list[OutputModel]
    metadata: list

    controller_components: list[ControllerComponentModel]

    controller_settings: ControllerSettingModel

    @classmethod
    def from_json(cls, file_path: str):
        """
        Load the configuration from a JSON file.
        """
        
        try:
            with open(file_path, "r") as f:
                config_data = json.load(f)
            return cls(**config_data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Couldn't load configuration from json file: {e}")

        except ValidationError as e:
            logger.error(e)
            raise ConfigError("Coudn't load configuration from json file")
