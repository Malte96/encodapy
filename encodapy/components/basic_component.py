"""
Description: This module provides basic components for the encodapy package.
Author: Martin Altenburger
"""

from datetime import datetime, timezone
from typing import Optional, Union, Type, Any
from loguru import logger
from pydantic import ValidationError
from encodapy.components.basic_component_config import (
    ComponentIOModel,
    ComponentValidationError,
    ControllerComponentModel,
    DataPointGeneral,
    IOAllocationModel,
    IOModell,
    ConfigDataPoints,
    InputData,
    ConfigData,
    OutputData
)
from encodapy.components.component_loader import (
    get_component_io_model,
    get_component_config_data_model,
    get_component_input_data_model,
    get_component_output_data_model
)

from encodapy.utils.models import (
    DataTransferComponentModel,
    InputDataEntityModel,
    InputDataModel,
    StaticDataEntityModel,
)
from encodapy.utils.units import DataUnits, get_unit_adjustment_factor

class BasicComponent:
    """
    Base class for all components in the encodapy package.
    This class provides basic functionality that can be extended by specific components.

    Contains methods for:
    - Getting component configuration: `get_component_config()`
    - Getting input values: `get_component_input()`
    - Setting all static data of the component: `set_component_static_data()`
    - Getting static data (by id): `get_component_static_data()`

    Args:
        config (Union[ControllerComponentModel, list[ControllerComponentModel]]):
            Configuration of the component or a list of configurations.
        component_id (str): ID of the component to get the configuration for.
        static_data (Optional[list[StaticDataEntityModel]]): Static data for the component.
    """

    def __init__(
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
        static_data: Optional[list[StaticDataEntityModel]] = None,
    ) -> None:
        if isinstance(config, ControllerComponentModel):
            self.component_config = ControllerComponentModel.model_validate(config)
        else:
            self.component_config = ControllerComponentModel.model_validate(
                self.get_component_config(config=config, component_id=component_id)
            )

        self.config_data: ConfigData
        self.set_component_config_data(
            static_data=static_data, static_config=self.component_config.config
        )
        # Inputs and Outputs of the component itsel
        self.io_model: Optional[ComponentIOModel] = None
        self.input_data: InputData

        self._prepare_i_o_config()

        self.prepare_component()

    def get_component_config(
        self, config: list[ControllerComponentModel], component_id: str
    ) -> ControllerComponentModel:
        """
        Function to get the configuration of a specific component from the service configuration
        Args:
            config (list[ControllerComponentModel]): List of all components in the configuration
            component_id (str): ID of the component to get the configuration
        Returns:
            ControllerComponentModel: Configuration of the component by ID

        Raises:
            ValueError: If the component with the given ID is not found in the configuration
        """
        for component in config:
            if component.id == component_id:
                return component

        raise KeyError(f"No component configuration found for {component_id}")

    def _get_input_and_output_config_models(self) -> tuple[Type[InputData], Type[OutputData]]:
        """
        Function to get the input and output models for the component.
        There needs to be a InputModel and a OutputModel in the config-module for the component.

        """
        component_input_model = get_component_io_model(
            component_type=self.component_config.type, model_subname="InputData"
        )
        component_output_model = get_component_io_model(
            component_type=self.component_config.type, model_subname="OutputData"
        )

        if not (
            issubclass(component_input_model, InputData)
            and issubclass(component_output_model, OutputData)
        ):
            error_msg = "Input or output model is not a subclass of BaseModel"
            logger.error(error_msg)
            raise TypeError(error_msg)

        return component_input_model, component_output_model

    def _prepare_i_o_config(self):
        """
        Function to prepare the I/O configuration for the component
        """
        component_input_model, component_output_model = self._get_input_and_output_config_models()
        config = self.component_config
        try:
            input_config = component_input_model.model_validate(
                config.inputs.root
                if isinstance(config.inputs, IOModell)
                else config.inputs
            )
        except ValidationError:
            error_msg = f"Invalid input configuration for the component {self.component_config.id}"
            logger.error(error_msg)
            raise

        try:
            output_config = component_output_model.model_validate(
                config.outputs.root
                if isinstance(config.outputs, IOModell)
                else config.outputs
            )
        except ValidationError:
            error_msg = f"Invalid output configuration for the component {self.component_config.id}"
            logger.error(error_msg)
            raise

        self.io_model = ComponentIOModel(input=input_config, output=output_config)

    def set_component_config_data(
        self,
        static_data: Union[list[StaticDataEntityModel], None],
        static_config: Optional[ConfigDataPoints] = None,
    ):
        """
        Function to get the value of the static data for a specific input configuration \
            of a component of the controller (or a individual one).

        Args:
            config_data (Union[list[StaticDataEntityModel], None]): Data of static entities
            static_config (Optional[ConfigDataPoints]): \
                Configuration of the static data, if available
                
        Raises:
            ComponentValidationError: If the static data configuration is invalid.

        """
        if static_config is None:
            logger.debug("No static config provided, skipping static data setup.")
            return
        if not isinstance(static_config, ConfigDataPoints):
            logger.error("Invalid static config provided.")
            raise ValueError("Invalid static config provided.")

        if static_data is None \
            and any(isinstance(value, IOAllocationModel) for value in static_config.root.values()):
            logger.error(
                "The component's static data could not be set: "
                "static_data is None but required by static_config."
            )
            return

        config_model = get_component_config_data_model(
            component_type=self.component_config.type, model_subname="ConfigData"
        )

        if config_model is None:
            logger.debug("No config model found, skipping static config check.")
            return

        static_config_data: dict[str, DataPointGeneral] = {}

        for datapoint_name, datapoint_config in config_model.model_fields.items():

            if datapoint_name not in static_config.root.keys() and datapoint_config.is_required():
                error_msg = (
                    f"Config entry '{datapoint_name}' is missing in the configuration "
                    f"of the component {self.component_config.id}."
                )
                logger.error(error_msg)
                raise ComponentValidationError(error_msg)

            unit_default = None
            if datapoint_config.json_schema_extra is not None \
                and isinstance(datapoint_config.json_schema_extra, dict) \
                and "unit" in datapoint_config.json_schema_extra:
                unit_default = DataUnits(datapoint_config.json_schema_extra["unit"])

            if datapoint_name not in static_config.root.keys():
                static_config_data[datapoint_name] = DataPointGeneral(
                    value=datapoint_config.default,
                    unit=unit_default
                )
                continue
            datapoint = static_config.root[datapoint_name]

            if isinstance(datapoint, DataPointGeneral):
                static_config_data[datapoint_name] = datapoint

            if isinstance(datapoint, IOAllocationModel):
                if static_data is None:
                    error_msg = (
                        f"Config entry '{datapoint_name}' needs static data but its not provided " 
                        f"to the component {self.component_config.id}."
                    )
                    logger.error(error_msg)
                    raise ComponentValidationError(error_msg)
                static_config_data[datapoint_name] = self.get_component_input(
                    input_entities=static_data,
                    input_config=datapoint
                )

            value = static_config_data[datapoint_name].value
            unit = static_config_data[datapoint_name].unit

            if unit_default is not None and unit is not None and unit != unit_default:

                if isinstance(value, (float, int)):
                    unit_adjustment_factor = get_unit_adjustment_factor(
                        unit_actual=unit,
                        unit_target=unit_default
                    )
                    if unit_adjustment_factor is None:
                        error_msg = (
                            f"Config entry '{datapoint_name}' has an invalid unit conversion from "
                            f"{static_config_data[datapoint_name].unit} to {unit_default}."
                        )
                        logger.error(error_msg)
                        raise ComponentValidationError(error_msg)

                    static_config_data[datapoint_name] = DataPointGeneral(
                        value=value * unit_adjustment_factor,
                        unit=unit_default
                    )
                else:
                    error_msg = (
                        f"Config entry '{datapoint_name}' has an invalid value type "
                        "to convert units. "
                        "This is only possible for numeric types (float or int)."
                    )
                    logger.error(error_msg)
                    raise ComponentValidationError(error_msg)

        # we need to convert the data to a dict of the correct types
        # because the config data model could contain different types
        for key, value in static_config_data.items():
            static_config_data[key] = value.model_dump()

        try:

            config_data_model = config_model.model_validate(
                static_config_data
            )

        except ValidationError as error:
            error_msg = (
                f"Error in static data configuration: {error}"
                " Could not validate and set the static data model"
            )
            logger.error(error_msg)
            raise ComponentValidationError(error_msg) from error

        self.config_data = config_data_model

    def get_component_input(
        self,
        input_entities: Union[
            list[InputDataEntityModel],
            list[StaticDataEntityModel],
            list[Union[InputDataEntityModel, StaticDataEntityModel]],
        ],
        input_config: IOAllocationModel,
    ) -> DataPointGeneral:
        """
        Function to get the value of the input data for a specific input configuration \
            of a component of the controller (or a individual one).

        Args:
            input_entities (list[InputDataEntityModel]): Data of input entities
            input_config (IOAllocationModel): Configuration of the input

        Returns:
            DataPointGeneral: The value of the input data and its unit and timestamp
        """
        for input_data in input_entities:
            if input_data.id == input_config.entity:
                for attribute in input_data.attributes:
                    if attribute.id == input_config.attribute:
                        return DataPointGeneral(
                            value=attribute.data,
                            unit=attribute.unit,
                            time=attribute.latest_timestamp_input
                        )

        raise KeyError(
            f"Input data {input_config.entity} / {input_config.attribute} not found. "
            "Please check the configuration of the Inputs, Outputs and Static Data."
        )

    def prepare_component(self):
        """
        Function to prepare the component.
        This function should be implemented in each component to prepare the component.
        """
        logger.debug("Prepare component is not implemented in the base class")

    def set_input_data(self, input_data: InputDataModel) -> None:
        """
        Set the input values for the component from the provided input entities.
        Needs to be implemented in each component.

        Args:
            input_data (InputDataModel): Input data model containing all necessary entities

        """
        if self.io_model is None:
            return
        # use all input datapoints, also the static data (flexible solution)
        input_datapoints: list[Union[InputDataEntityModel, StaticDataEntityModel]] = []
        input_datapoints.extend(input_data.input_entities)
        input_datapoints.extend(input_data.static_entities)

        input_values: dict[str, DataPointGeneral] = {}

        for datapoint_name, datapoint_config in self.io_model.input.__dict__.items():
            if datapoint_config is None:
                continue
            try:
                datapoint_config = IOAllocationModel.model_validate(datapoint_config)
            except ValidationError as e:
                logger.warning(
                    f"Invalid input configuration for {datapoint_name} "
                    f"in {self.component_config.id}: {e}"
                    )
                continue

            input_datapoint = self.get_component_input(
                input_entities=input_datapoints,
                input_config=datapoint_config
            )
            if input_datapoint.value is None:
                input_datapoint.value = datapoint_config.default
            if input_datapoint.unit is None:
                input_datapoint.unit = datapoint_config.unit
            input_values[datapoint_name] = DataPointGeneral(
                value=input_datapoint.value,
                unit=input_datapoint.unit,
                time=input_datapoint.time
            )

        input_data_model = get_component_input_data_model(
            component_type=self.component_config.type
            )
        input_values_raw: dict[str, Any] = {}
        for key, value in input_values.items():
            input_values_raw[key] = value.model_dump()

        self.input_data = input_data_model.model_validate(input_values_raw)

    def run(self, data: InputDataModel) -> list[DataTransferComponentModel]:
        """
        Run the component.
        
        Args:
            data (InputDataModel): Input data for the component, \
                including all necessary entities.
        Returns:
            list[DataTransferComponentModel]: List of data transfer components.
        """
        components: list[DataTransferComponentModel] = []

        if self.io_model is None:
            logger.warning(f"IOModel of {self.component_config.id} is not set.")
            return components

        try:
            self.set_input_data(input_data=data)
        except (ValueError, KeyError) as e:
            logger.error(
                f"Setting input data failed for {self.component_config.id}: {e}"
            )
            return components

        # TODO use the output model to hold and validate the output values
        # would be easier to use
        # no information about calculation function needed, only a calculation is required

        # avoid: Instance of 'FieldInfo' has no 'model_fields' memberPylintE1101:no-member
        try:
            _, component_output_model = self._get_input_and_output_config_models()

            if hasattr(self.io_model.output, 'model_dump'):
                output_model = self.io_model.output.model_dump()
            else:
                raise ValidationError("Output model is not valid")

            output = component_output_model.model_validate(output_model)
        except ValidationError as e:
            logger.error(
                f"Output validation failed for {self.component_config.id}: {e}"
            )
            return components

        for output_datapoint_name, output_datapoint_info in output.model_fields.items():
            if (
                isinstance(output_datapoint_info.json_schema_extra, dict)
                and "calculation" in output_datapoint_info.json_schema_extra
            ):
                calculation_function = output_datapoint_info.json_schema_extra[
                    "calculation"
                ]
                if (
                    isinstance(calculation_function, str)
                    and calculation_function is not None
                ):
                    calculation_function = calculation_function.strip()
                else:
                    logger.warning(
                        f"No calculation method found for {output_datapoint_name} "
                        f"in {self.component_config.id}."
                    )
                    continue
            else:
                logger.warning(
                    f"No calculation method found for {output_datapoint_name} "
                    f"in {self.component_config.id}."
                )
                continue

            output_datapoint_config: Optional[IOAllocationModel] = getattr(
                self.io_model.output, output_datapoint_name
            )

            if output_datapoint_config is None:
                continue

            result_value, result_unit = getattr(self, calculation_function)()

            components.append(
                DataTransferComponentModel(
                    entity_id=output_datapoint_config.entity,
                    attribute_id=output_datapoint_config.attribute,
                    value=result_value,
                    unit=result_unit,
                    timestamp=datetime.now(timezone.utc),
                )
            )
            logger.debug(
                f"Calculated {output_datapoint_name}: {result_value} {result_unit} "
                f"for {self.component_config.id}."
            )

        return components

    def calibrate(
        self,
        static_data: Optional[list[StaticDataEntityModel]] = None,
    ):
        """
        Calibrate the component
        - This function updates the static data \
            and prepares the component for operation with the new static data
        - This function can be used to adjust parameters of the component, \
            so it needs to be extended
        Args:
            static_data (Optional[list[StaticDataEntityModel]]): Static data for the component
        """
        if static_data is not None:
            try:
                logger.debug(
                    f"Reloading static data for the component {self.component_config.id}"
                )
                self.set_component_config_data(
                    static_data=static_data, static_config=self.component_config.config
                )
                self.prepare_component()
            except ComponentValidationError as e:
                logger.error(f"Failed to reload static data for {self.component_config.id}: {e}")
                raise
