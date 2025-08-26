"""
Description: This module provides basic components for the encodapy package.
Author: Martin Altenburger
"""
from typing import Dict, List, Optional, Union, Type
from datetime import datetime, timezone
from loguru import logger
from pandas import DataFrame
from pydantic import BaseModel, ValidationError
from encodapy.components.basic_component_config import (
    ControllerComponentModel,
    ControllerComponentStaticData,
    DataPointModel,
    IOAllocationModel,
    IOModell,
    ComponentIOModel,
    InputModel,
    OutputModel,
    ComponentValidationError
)
from encodapy.utils.models import (
    DataUnits,
    InputDataEntityModel,
    StaticDataEntityModel,
    InputDataModel,
    DataTransferComponentModel
    )
from encodapy.components.component_loader import (
    get_component_io_model,
    get_component_static_data_model
)

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

        self.static_data = ControllerComponentStaticData({})
        self.set_component_static_data(
            static_data, static_config=self.component_config.staticdata
        )
        # Inputs and Outputs of the component itsel
        self.io_model: Optional[ComponentIOModel] = None

        self.prepare_basic_component()

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

    def get_component_input(
        self,
        input_entities: Union[
            list[InputDataEntityModel],
            list[StaticDataEntityModel],
            list[Union[InputDataEntityModel, StaticDataEntityModel]]],
        input_config: IOAllocationModel,
    ) -> tuple[
        Union[str, float, int, bool, Dict, List, DataFrame, None],
        Union[DataUnits, None],
    ]:
        """
        Function to get the value of the input data for a spesific input configuration \
            of a component of the controller (or a inividual one).

        Args:
            input_entities (list[InputDataEntityModel]): Data of input entities
            input_config (IOAllocationModel): Configuration of the input

        Returns:
            tuple[Union[str, float, int, bool, Dict, List, DataFrame, None], \
                Union[DataUnits, None]]: The value of the input data and its unit
        """
        for input_data in input_entities:
            if input_data.id == input_config.entity:
                for attribute in input_data.attributes:
                    if attribute.id == input_config.attribute:
                        return attribute.data, attribute.unit

        raise KeyError(f"Input data {input_config.entity} / {input_config.attribute} not found. "
                         "Please check the configuration of the Inputs, Outputs and Static Data.")

    def set_component_static_data(
        self,
        static_data: Union[list[StaticDataEntityModel], None],
        static_config: Union[IOAllocationModel, IOModell, None],
    ):
        """
        Function to get the value of the static data for a spesific input configuration \
            of a component of the controller (or a inividual one).

        Args:
            static_data (Union[list[StaticDataEntityModel], None]): Data of static entities
            static_config (Union[IOAllocationModel, IOModell, None]): \
                Configuration of the static data

        """

        if static_config is None:
            logger.debug("No static config provided, skipping static data setup.")
            return

        if static_data is None:
            logger.warning("The component's static data could not be set: "
                           "static_data is None.")
            return
            # Do not overwrite the static data if not data is available or no static config is given

        static_config_data = {}
        number_static_datapoints = 0

        if isinstance(static_config, IOModell):
            for static_config_item in static_config.root.keys():
                datapoint_value, datapoint_unit = self.get_component_input(
                    input_entities=static_data,
                    input_config=static_config.root[static_config_item],
                )
                static_config_data[static_config_item] = (
                    DataPointModel(
                        value=datapoint_value, unit=datapoint_unit
                    )
                )
                number_static_datapoints += 1
        elif isinstance(static_config, IOAllocationModel):
            datapoint_value, datapoint_unit = self.get_component_input(
                input_entities=static_data,
                input_config=static_config,
            )
            static_config_data[static_config.entity] = (
                DataPointModel(
                    value=datapoint_value, unit=datapoint_unit
                )
            )
            number_static_datapoints += 1
        else:
            raise ValueError("Unsupported static config type")
        try:
            static_data_model = ControllerComponentStaticData.model_validate(
                static_config_data
            )
        except ValidationError as error:
            logger.error(f"Error in static data configuration: {error}"
                         " Could not validate and set the static data model")
            return

        static_config_available = len(static_data_model.root.keys()) == number_static_datapoints

        if not static_config_available:
            logger.error(
                "Static data configuration does not match the component configuration. "
                "Please check the configuration."
            )
            return
        self.static_data = static_data_model

    def prepare_basic_component(self):
        """
        Function for preparing the start of the component:
            - Preparing the I/O configuration.
            - Checking the static configuration.
            - Starting the function for individual preparation steps.
        """

        self._prepare_i_o_config()

        self._check_static_config()

        self.prepare_component()


    def _get_input_and_output_models(self) -> tuple[Type[BaseModel], Type[BaseModel]]:
        """
        Function to get the input and output models for the component.
        There needs to be a InputModel and a OutputModel in the config-module for the component.
        
        #TODO maybe we could use the module-path for different modules?
        """
        component_input_model = get_component_io_model(
            component_type = self.component_config.type,
            model_subname = "InputModel"
        )
        component_output_model = get_component_io_model(
            component_type = self.component_config.type,
            model_subname = "OutputModel"
        )

        if not (issubclass(component_input_model, InputModel) and
                issubclass(component_output_model, OutputModel)):
            error_msg = (
                "Input or output model is not a subclass of BaseModel")
            logger.error(error_msg)
            raise TypeError(error_msg)

        return component_input_model, component_output_model

    def _prepare_i_o_config(self):
        """
        Function to prepare the I/O configuration for the two-point controller
        """
        config = self.component_config
        component_input_model, component_output_model = self._get_input_and_output_models()
        try:
            input_config = component_input_model.model_validate(
                config.inputs.root if isinstance(config.inputs, IOModell)
                else config.inputs)
        except ValidationError:
            error_msg = f"Invalid input configuration for the component {self.component_config.id}"
            logger.error(error_msg)
            raise

        try:
            output_config = component_output_model.model_validate(
                config.outputs.root if isinstance(config.outputs, IOModell)
                else config.outputs)
        except ValidationError:
            error_msg = f"Invalid output configuration for the component {self.component_config.id}"
            logger.error(error_msg)
            raise

        self.io_model = ComponentIOModel(
            input=input_config,
            output=output_config
            )

    def _check_static_config(self):
        """
        Check the static configuration of the component.
        Uses the model of the required static data to validate the configuration.
        
        Raises:
            ComponentValidationError: If the validation fails because static data is missing.
        """
        static_model = get_component_static_data_model(
            component_type=self.component_config.type,
            model_subname="StaticData"
        )
        if static_model is None:
            logger.debug("No static model found, skipping static config check.")
            return

        for static_datapoint in static_model.__members__:

            static_name = static_model[static_datapoint].value

            if static_name not in self.component_config.staticdata.root.keys():
                logger.error(f"Static data '{static_name}' is missing in the configuration "
                             f"of the component {self.component_config.id}.")
                raise ComponentValidationError(
                    f"Static data '{static_name}' is missing in the configuration. "
                             f"of the component {self.component_config.id}.")

    def get_component_static_data(
        self,
        component_id: str,
        unit: Optional[DataUnits] = None
    ) -> tuple[
        Union[str, float, int, bool, Dict, List, DataFrame, None],
        Optional[DataUnits]
    ]:
        """
        Function to get the static data of a component by its ID \
            and in the specified unit (optional).
        Args:
            component_id (str): ID of the component to get the static data for
            unit (Optional[str]): Unit to convert the static data value to, if specified
        Returns:
            Union[str, float, int, bool, Dict, List, DataFrame, None]: 
                The value of the static data in the specified unit or as is if no unit is specified
        """
        if component_id not in self.static_data.root.keys():
            return None, None

        static_data = DataPointModel.model_validate(
            self.static_data.root.get(component_id, None)
        )
        static_data_value = static_data.value
        static_data_unit = static_data.unit

        if unit is not None and static_data_unit is not None:
            if static_data_unit == unit:
                return static_data_value, static_data_unit
            # TODO: Implement unit conversion if needed
            raise RuntimeError(
                f"Unit conversion from {static_data_unit} to {unit} is not implemented"
            )

        return static_data_value, static_data_unit

    def prepare_component(self):
        """
        Function to prepare the component.
        This function should be implemented in each component to prepare the component.
        """
        logger.debug("Prepare component is not implemented in the base class")

    def set_input_values(self,
                         input_data: InputDataModel
                         ) -> None:
        """
        Set the input values for the component from the provided input entities.
        Needs to be implemented in each component.
        TODO: Is this possible in the basic component?

        Args:
            input_data (InputDataModel): Input data model containing all necessary entities

        """
        _input_data = input_data
        logger.debug("Input values should be set in each component")


    def run(self,
            data: InputDataModel
            )-> list[DataTransferComponentModel]:
        """
        Run the component.
        
        Args:
            data (InputDataModel): Input data for the component, \
                including all necessary entities.
        Returns:
            list[DataTransferComponentModel]: List of data transfer components.
        """
        components:list[DataTransferComponentModel] = []

        if self.io_model is None:
            logger.warning(f"IOModel of {self.component_config.id} is not set.")
            return components

        try:
            self.set_input_values(input_data=data)
        except (ValueError, KeyError) as e:
            logger.error(f"Setting input values failed for {self.component_config.id}: {e}")
            return components

        # avoid: Instance of 'FieldInfo' has no 'model_fields' memberPylintE1101:no-member
        try:
            _, component_output_model = self._get_input_and_output_models()
            output = component_output_model.model_validate(self.io_model.output)
        except ValidationError as e:
            logger.error(f"Output validation failed for {self.component_config.id}: {e}")
            return components

        for output_datapoint_name, output_datapoint_info in output.model_fields.items():

            if (isinstance(output_datapoint_info.json_schema_extra, dict)
                and "calculation" in output_datapoint_info.json_schema_extra):
                calculation_function = output_datapoint_info.json_schema_extra["calculation"]
                if isinstance(calculation_function, str) and calculation_function is not None:
                    calculation_function = calculation_function.strip()
                else:
                    logger.warning(f"No calculation method found for {output_datapoint_name} "
                                   f"in {self.component_config.id}.")
                    continue
            else:
                logger.warning(f"No calculation method found for {output_datapoint_name} "
                               f"in {self.component_config.id}.")
                continue

            output_datapoint_config: Optional[IOAllocationModel] = getattr(
                self.io_model.output,
                output_datapoint_name)

            if output_datapoint_config is None:
                continue

            result_value, result_unit = getattr(self, calculation_function)()

            components.append(DataTransferComponentModel(
                entity_id=output_datapoint_config.entity,
                attribute_id=output_datapoint_config.attribute,
                value=result_value,
                unit=result_unit,
                timestamp=datetime.now(timezone.utc)
            ))
            logger.debug(f"Calculated {output_datapoint_name}: {result_value} {result_unit} "
                         f"for {self.component_config.id}.")

        return components

    def calibrate(self,
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
            logger.debug(f"Reloading static data for the component {self.component_config.id}")
            self.set_component_static_data(
                static_data=static_data,
                static_config=self.component_config.staticdata
            )
            self.prepare_component()
