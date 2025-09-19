"""
Description: This file contains the class FiwareConnections,
which is used to store the connection parameters for the Fiware and CrateDB connections.
Author: Paul Seidel
"""

import os
import json
import pathlib
from datetime import datetime
from typing import Union, Optional
from loguru import logger
import pandas as pd
from pydantic import ValidationError
from encodapy.config import (
    AttributeModel,
    AttributeTypes,
    CommandModel,
    DataQueryTypes,
    DefaultEnvVariables,
    FileExtensionTypes,
    InputModel,
    OutputModel,
    StaticDataModel,
    DataFile,
)
from encodapy.utils.models import (
    InputDataAttributeModel,
    InputDataEntityModel,
    OutputDataEntityModel,
    StaticDataEntityModel,
)
from encodapy.utils.error_handling import NotSupportedError


class FileConnection:
    """
    Class for the connection to a local file.
    Only a helper class.
    """

    def __init__(self):
        self.file_params = {}

    def load_file_params(self):
        """
        Function to load the file parameters
        """
        logger.debug("Load config for File interface")
        self.file_params["PATH_OF_INPUT_FILE"] = os.environ.get(
            "PATH_OF_INPUT_FILE", DefaultEnvVariables.PATH_OF_INPUT_FILE.value
        )
        self.file_params["START_TIME_FILE"] = os.environ.get(
            "START_TIME_FILE", DefaultEnvVariables.START_TIME_FILE.value
        )
        self.file_params["PATH_OF_STATIC_DATA"] = os.environ.get(
            "PATH_OF_STATIC_DATA", DefaultEnvVariables.PATH_OF_STATIC_DATA.value
        )

    def _get_last_timestamp_for_file_output(
        self, output_entity: OutputModel
    ) -> tuple[OutputDataEntityModel, Union[datetime, None]]:
        """
        Function to get the latest timestamps of the output entity from a File, if exitst

        Args:
            output_entity (OutputModel): Output entity

        Returns:
            tuple[OutputDataEntityModel, Union[datetime, None]]:
                - OutputDataEntityModel with timestamps for the attributes
                - the latest timestamp of the output entity for the attribute
                with the oldest value (None if no timestamp is available)
        TODO:
            - is it really nessesary to get a timestamp for file-calculations /
            during calculation time is set to input_time
        """

        output_id = output_entity.id_interface

        timestamps = []
        timestamp_latest_output = None

        return (
            OutputDataEntityModel(id=output_id, attributes_status=timestamps),
            timestamp_latest_output,
        )

    def get_data_from_file(
        self,
        method: DataQueryTypes,
        entity: InputModel,
    ) -> Union[InputDataEntityModel, None]:
        """f
        Function to check input data-file and load data, \
        check of the file extension (compare in lower cases)

        Args:
            method (DataQueryTypes): Keyword for type of query
            entity (InputModel): Input entity

        Raises:
            NotSupportedError: If the file extension is not supported

        Returns:
            Union[InputDataEntityModel, None]: Model with the input data or \
                None if no data is available
        """

        file_extension = pathlib.Path(
            self.file_params["PATH_OF_INPUT_FILE"]
        ).suffix.lower()

        if file_extension == FileExtensionTypes.CSV.value:
            logger.debug(f"load inputdata from {file_extension} -file")
            data = self.get_data_from_csv_file(method=method, entity=entity)
        elif file_extension == FileExtensionTypes.JSON.value:
            logger.debug(f"load inputdata from {file_extension} -file")
            data = self.get_data_from_json_file(method=method, entity=entity)
        else:
            logger.debug(f"File extension {file_extension} is not supported")
            raise NotSupportedError

        return data

    def get_data_from_csv_file(
        self,
        method: DataQueryTypes,
        entity: InputModel,
    ) -> Union[InputDataEntityModel, None]:
        """
            Function to read input data for calculations from a input file.
            first step: read the first values in the file / id_inputs.
            Then get the data from the entity since the last timestamp
            of the output entity from cratedb.
        Args:
            - method (DataQueryTypes): Keyword for type of query
            - entity (InputModel): Input entity
        TODO:
             - handle the methods for the file interface

        Returns:
            - InputDataEntityModel: Model with the input data or None if the connection
            to the platform is not available

        """
        # TODO: Implement method handling for file interface
        _ = method  # Acknowledge unused parameter

        # attributes_timeseries = {}
        attributes_values = []
        path_of_file = self.file_params["PATH_OF_INPUT_FILE"]
        try:
            data = pd.read_csv(path_of_file, sep=";", parse_dates=["Time"], decimal=",")
            # Add tz to time index, if not in iso format
            data["Time"] = [self._read_time_from_string(item) for item in data["Time"]]
            data.set_index("Time", inplace=True)
            print(data)
        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"Could not open file ({path_of_file}): {e}")
            return None
        except (pd.errors.EmptyDataError,
                pd.errors.ParserError,
                ValueError,
                UnicodeDecodeError) as e:
            logger.error(f"Error reading CSV file ({path_of_file}): {e}")
            return None
        for attribute in entity.attributes:

            if attribute.type == AttributeTypes.TIMESERIES:
                # attributes_timeseries[attribute.id] = attribute.id_interface
                logger.warning(
                    f"Attribute type {attribute.type} for attribute {attribute.id}"
                    f"of entity {entity.id} not supported."
                )
            elif attribute.type == AttributeTypes.VALUE:
                attributes_values.append(
                    InputDataAttributeModel(
                        id=attribute.id,
                        data=data[attribute.id_interface].iloc[0],
                        data_type=AttributeTypes.VALUE,
                        data_available=True,
                        latest_timestamp_input=data.index[0],
                    )
                )
            else:
                logger.warning(
                    f"Attribute type {attribute.type} for attribute {attribute.id}"
                    f"of entity {entity.id} not supported."
                )

        return InputDataEntityModel(id=entity.id, attributes=attributes_values)

    def _read_time_from_string(self, time_string: str|datetime|None) -> Optional[datetime]:
        """
        Helper function to read a time from a string based on the configured time format.
        Args:
            time_string (str): The time string to parse.
        Returns:
            Optional[datetime]: The parsed datetime object, or None if parsing fails.
        """
        if time_string is None:
            return None
        if isinstance(time_string, datetime):
            if time_string.tzinfo is None:
                logger.debug(
                    f"Time '{time_string}' has no timezone info. "
                    f"Assuming local timezone."
                )
                time_string = time_string.astimezone()
            return time_string

        try:
            time = datetime.fromisoformat(time_string)
            if time.tzinfo is None:
                logger.debug(
                    f"Time string '{time_string}' has no timezone info. "
                    f"Assuming local timezone."
                )
                time = time.astimezone()
            return time
        except ValueError:
            logger.debug(
                f"Time string '{time_string}' is not in ISO format. "
                f"Attempting to parse with format {self.file_params['TIME_FORMAT_FILE']}."
            )
            return None

    def _get_data_from_json_file(
        self,
        entity: StaticDataModel|InputModel,
        path_of_file: str,
        data_type:str
        ) -> Union[InputDataEntityModel, StaticDataEntityModel, None]:
        try:
            # read data from json file and timestamp
            with open(path_of_file, encoding="utf-8") as f:
                data_file = json.load(f)
        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"File not found / not readable ({path_of_file}) "
                         f"for {data_type}: {e}")
            return None
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as e:
            logger.error(f"Error decoding JSON from file ({path_of_file})"
                         f"for {data_type}: {e}")
            return None

        if isinstance(data_file, list):
            data_file = {"data": data_file}
        elif isinstance(data_file, dict):
            data_file = {"data": data_file.get(data_type, [])}
        else:
            logger.error(f"Unsupported data format ({path_of_file}) for {data_type}")
            return None

        try:
            data = DataFile.model_validate(data_file)
        except ValidationError as e:
            logger.error(f"Validation error for file ({path_of_file}) for {data_type}: {e}")
            return None
        attributes_values = []
        for attribute in entity.attributes:

            for item_entity in data.data:
                for item_attribute in item_entity.attributes:
                    try:
                        if item_attribute.id == attribute.id:

                            attributes_values.append(
                                InputDataAttributeModel(
                                    id=attribute.id,
                                    data=item_attribute.value,
                                    unit=item_attribute.unit,
                                    data_type=AttributeTypes.VALUE,
                                    data_available=True,
                                    latest_timestamp_input= \
                                    self._read_time_from_string(item_attribute.time),
                                )
                            )

                    except (ValueError, TypeError) as e:
                        logger.error(
                            f"Error processing attribute {attribute.id} "
                            f"in file ({path_of_file}) for {data_type}: {e}"
                        )
                        continue
        if isinstance(entity, StaticDataModel):
            return StaticDataEntityModel(id=entity.id, attributes=attributes_values)

        return InputDataEntityModel(id=entity.id, attributes=attributes_values)

    def get_data_from_json_file(
        self,
        method: DataQueryTypes,
        entity: InputModel,
    ) -> Optional[InputDataEntityModel]:
        """
            Function to read input data for calculations from a input file.
            first step: read the keys and values in the file / id_inputs.
            Then get the data from the entity since the last timestamp
            of the output entity from cratedb.
        Args:
            - method (DataQueryTypes): Keyword for type of query
            - entity (InputModel): Input entity
        TODO:
             - timestamp_latest_output (datetime): Timestamp of the input value
             -  -> seperating Data in Calculation or here ??
             - handle the methods for the file interface

        Returns:
            - InputDataEntityModel: Model with the input data or None if the connection
            to the platform is not available

        """
        # TODO: Implement method handling for file interface
        _ = method  # Acknowledge unused parameter

        # attributes_timeseries = {}

        data = self._get_data_from_json_file(
            entity=entity,
            path_of_file=self.file_params["PATH_OF_INPUT_FILE"],
            data_type="inputdata"
        )
        if not isinstance(data, InputDataEntityModel):
            return None
        return data

    def get_staticdata_from_file(
        self,
        entity: StaticDataModel,
    ) -> Union[StaticDataEntityModel, None]:
        """
        Function to read static data for calculations from config file.
        Args:
            - entity (StaticDataModel): Input entity
        TODO:
            - work with timeseries, for example: timetable with presence or heating_times

        Returns:
            - StaticDataEntityModel: Model with the static data

        """

        data = self._get_data_from_json_file(
            entity=entity,
            path_of_file=self.file_params["PATH_OF_STATIC_DATA"],
            data_type="staticdata"
        )
        if not isinstance(data, StaticDataEntityModel):
            return None
        return data


    def send_data_to_json_file(
        self,
        output_entity: OutputModel,
        output_attributes: list[AttributeModel],
        output_commands: list[CommandModel],
    ) -> None:
        """_Function to create a json_file in result-folder

        Args:
            output_entity (OutputModel): _description_
            output_attributes (list[AttributeModel]): _description_
            output_commands (list[CommandModel]): _description_

        Out: Json-file

        TODO:
            - Is it better to set the results-folder via env?
        """
        outputs = []
        output_attr = []
        commands = []
        logger.debug("Write outputs to json-output-files")

        if not os.path.exists("./results"):
            os.makedirs("./results")

        for output in output_attributes:
            output_attr.append(
                {
                    "id": output.id_interface,
                    "value": output.value,
                    "unit": None if output.unit is None else output.unit.value,
                    "time": None if output.timestamp is None else output.timestamp.isoformat(" ")
                }
            )
        outputs.append(
            {
                "id": output_entity.id,
                "attributes" : output_attr
            }
        )
        try:
            with open(
                f"./results/outputs_{str(output_entity.id)}.json", "w", encoding="utf-8"
            ) as outputfile:
                json.dump(outputs, outputfile)
        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"Error writing output file: {e}")
            raise

        for command in output_commands:
            commands.append(
                {
                    "id_interface": command.id_interface,
                    "value": command.value,
                    "unit": command.unit.value,
                    "time": command.timestamp.isoformat(" ")                    
                }
            )

        with open("./results/commands.json", "w", encoding="utf-8") as commandfile:
            json.dump(commands, commandfile)
