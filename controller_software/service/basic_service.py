# Module for the basic service class for the data processing and transfer via different interfaces.
# TODO: The class is not yet finished and needs to be extended with the necessary functions and methods. -- Martin Altenburger
# TODO: Import the necessary modules and classes - improve the imports -- Martin Altenburger
# Author: Martin Altenburger
# ----------------------------------------
import os
import pathlib
from asyncio import sleep
from datetime import datetime, timedelta, timezone
from typing import Union
import numpy as np
import pandas as pd
import requests
from dateutil import tz
from loguru import logger

from controller_software.config import (
    AttributeModel,
    AttributeTypes,
    CommandModel,
    ConfigModel,
    DefaultEnvVariables,
    InputModel,
    Interfaces,
    OutputModel,
    TimerangeTypes,
    DataQueryTypes,
    FileExtensionTypes
)

from controller_software.utils.cratedb import CrateDBConnection
from controller_software.utils.error_handling import NotSupportedError, NoCredentials
from controller_software.utils.fiware_auth import BaererToken
from controller_software.utils.health import update_health_file
from controller_software.utils.logging import LoggerControl
from controller_software.utils.models import (
    DataTransferModel,
    InputDataAttributeModel,
    InputDataEntityModel,
    InputDataModel,
    ContextDataModel,
    OutputDataAttributeModel,
    OutputDataEntityModel,
    OutputDataModel,
)
from controller_software.utils.timeunit import get_time_unit_seconds

from filip.clients.ngsi_v2 import ContextBrokerClient
from filip.models.base import DataType, FiwareHeaderSecure
from filip.models.ngsi_v2.base import NamedMetadata
from filip.models.ngsi_v2.context import NamedCommand, NamedContextAttribute

# from IPython.display import display


class ControllerBasicService:
    """
    Class for processing the measurement data including data transfer to a FIWARE platform.

    TODO: Implement the other interfaces(FILE, MQTT, ...)

    """

    def __init__(
        self,
    ) -> None:
        self.config = None
        self.logger = LoggerControl()

        self.fiware_params = {}
        self.database_params = {}
        self.fiware_token = {}
        self.fiware_token_client = None
        self.fiware_header = None
        self.cb_client = None
        self.crate_db_client = None

        self.file_params = {}
        self.reload_contextdata = None
        self.contextdata = None

        self.timestamp_health = None

    def _load_config(self):
        """
        Function loads the env of the service from the configuration file (.env).

        TODO: Is it simpler to use the configuration file directly?

        """
        config_path = os.environ.get(
            "CONFIG_PATH", DefaultEnvVariables.CONFIG_PATH.value
        )
        
        self.config = ConfigModel.from_json(file_path=config_path)
        
        if self.config.interfaces.fiware:

            self.fiware_params["cb_url"] = os.environ.get(
                "CB_URL", DefaultEnvVariables.CB_URL.value
            )
            self.fiware_params["service"] = os.environ.get(
                "FIWARE_SERVICE", DefaultEnvVariables.FIWARE_SERVICE.value
            )
            self.fiware_params["service_path"] = os.environ.get(
                "FIWARE_SERVICE_PATH", DefaultEnvVariables.FIWARE_SERVICE_PATH.value
            )
            self.fiware_token["authentication"] = os.getenv(
                "FIWARE_AUTH", str(DefaultEnvVariables.FIWARE_AUTH.value)
            ).lower() in ("true", "1", "t")

            if self.fiware_token["authentication"]:

                if (
                    os.environ.get("FIWARE_CLIENT_ID") is not None
                    and os.environ.get("FIWARE_CLIENT_PW") is not None
                    and os.environ.get("FIWARE_TOKEN_URL") is not None
                ):
                    self.fiware_token["client_id"] = os.environ.get("FIWARE_CLIENT_ID")
                    self.fiware_token["client_secret"] = os.environ.get(
                        "FIWARE_CLIENT_PW"
                    )
                    self.fiware_token["token_url"] = os.environ.get("FIWARE_TOKEN_URL")
                elif os.environ.get("FIWARE_BAERER_TOKEN") is not None:
                    self.fiware_token["baerer_token"] = os.environ.get(
                        "FIWARE_BAERER_TOKEN"
                    )
                else:
                    logger.error("No authentication credentials available")
                    raise NoCredentials

            self.database_params["crate_db_url"] = os.environ.get(
                "CRATE_DB_URL", DefaultEnvVariables.CRATE_DB_URL.value
            )
            self.database_params["crate_db_user"] = os.environ.get(
                "CRATE_DB_USER", DefaultEnvVariables.CRATE_DB_USER.value
            )
            self.database_params["crate_db_pw"] = os.environ.get(
                "CRATE_DB_PW", DefaultEnvVariables.CRATE_DB_PW.value
            )
            self.database_params["crate_db_ssl"] = os.environ.get(
                "CRATE_DB_SSL", str(DefaultEnvVariables.CRATE_DB_SSL.value)
            ).lower() in ("true", "1", "t")

        if self.config.interfaces.file:
            logger.info("Load config for File interface")
            self.file_params["PATH_OF_INPUT_FILE"] = os.environ.get(
                "PATH_OF_INPUT_FILE", DefaultEnvVariables.PATH_OF_INPUT_FILE.value
            )
            self.file_params["START_TIME_FILE"] = os.environ.get(
                "START_TIME_FILE", DefaultEnvVariables.START_TIME_FILE.value
            )
            self.file_params["TIME_FORMAT_FILE"] = os.environ.get(
                "TIME_FORMAT_FILE", DefaultEnvVariables.TIME_FORMAT_FILE.value
            )

        if self.config.interfaces.mqtt:
            logger.warning("MQTT interface not implemented yet.")
            raise NotSupportedError

        self.reload_contextdata = os.getenv( "RELOAD_CONTEXTDATA", str(DefaultEnvVariables.RELOAD_CONTEXTDATA.value)).lower() in ("true", "1", "t")
        

        logger.debug("ENVs succesfully loaded.")

        return config_path

    async def prepare_basic_start(self):
        """
        Function to create important objects with the configuration from the configuration file (.env) and prepare the start basics of the service.

        TODO:
            - Implement the other interfaces(FILE, MQTT, ...)

        """
        
        self._load_config()
                
        
        if self.config.interfaces.fiware:
            if self.fiware_token["authentication"]:
                if "baerer_token" in self.fiware_token:
                    self.fiware_token_client = BaererToken(
                        token=self.fiware_token["baerer_token"]
                    )
                else:
                    self.fiware_token_client = BaererToken(
                        client_id=self.fiware_token["client_id"],
                        client_secret=self.fiware_token["client_secret"],
                        token_url=self.fiware_token["token_url"],
                    )
                self.fiware_header = FiwareHeaderSecure(
                    service=self.fiware_params["service"],
                    service_path=self.fiware_params["service_path"],
                    authorization=self.fiware_token_client.baerer_token,
                )
            else:
                self.fiware_header = FiwareHeaderSecure(
                    service=self.fiware_params["service"],
                    service_path=self.fiware_params["service_path"],
                )

            self.cb_client = ContextBrokerClient(
                url=self.fiware_params["cb_url"], fiware_header=self.fiware_header
            )

            self.crate_db_client = CrateDBConnection(
                crate_db_url=self.database_params["crate_db_url"],
                crate_db_user=self.database_params["crate_db_user"],
                crate_db_pw=self.database_params["crate_db_pw"],
                crate_db_ssl=self.database_params["crate_db_ssl"],
            )
        if self.config.interfaces.file:
            
            # maybe it is nessesary to check which tiype of data file exits csv or json
            # function to return the file extension
            file_extension = pathlib.Path(self.file_params["PATH_OF_INPUT_FILE"]).suffix

            if file_extension == FileExtensionTypes.CSV.value:
                logger.info(f"load config for {file_extension} -file")
            elif file_extension == FileExtensionTypes.JSON.value:
                logger.info(f"load config for {file_extension} -file")
            else:
                logger.info(f"File extension {file_extension} is not supported") 
                raise NotSupportedError
            

        if self.config.interfaces.mqtt:
            logger.warning("MQTT interface not implemented yet.")
            raise NotSupportedError




        return

    async def prepare_start(self):
        """
        Function prepare the start of the service (calls the function for the basic preparing)

        """
        logger.info("Prepare Start of Service")

        await self.prepare_basic_start()

    def _calculate_dates(
        self,
        method: DataQueryTypes,
        last_timestamp: Union[datetime, None]
    ) -> tuple[str, str]:
        """Function to calculate the dates for the input data query

        Args:
            method (DataQueryTypes): Method for the calculation
            time_now (datetime): Time now
            last_timestamp (datetime): Timestamp of the last output

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """

        time_now = datetime.now(timezone.utc)
        if last_timestamp is None:
            timeframe = 0
        else:
            timeframe = (time_now - last_timestamp).total_seconds() / 60
        from_date, to_date = None, None

        if method is DataQueryTypes.CALCULATION:
            from_date, to_date = self._handle_calculation_method(
                time_now, last_timestamp, timeframe
            )
        elif method is DataQueryTypes.CALIBRATION:
            from_date, to_date = self._handle_calibration_method(last_timestamp)

        if to_date is None:
            to_date = time_now.strftime("%Y-%m-%dT%H:%M:%S%z")

        return from_date, to_date

    def _handle_calculation_method(
        self,
        time_now: datetime,
        last_timestamp: datetime,
        timeframe: int,
    ) -> tuple[str, str]:
        """Funtion to calculate the dates for the calculation method

        Args:
            time_now (datetime): Time now
            last_timestamp (datetime): Timestamp of the last output
            timeframe (timerange): Timeframe between now and the last output in seconds

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """
        calculation = self.config.controller_settings.time_settings.calculation

        if calculation.timerange is not None:
            return self._calculate_timerange(
                time_now,
                last_timestamp,
                timeframe,
                calculation.timerange,
                calculation.timerange_type,
                get_time_unit_seconds(calculation.timerange_unit),
            )
        if (
            calculation.timerange_min is not None
            and calculation.timerange_max is not None
        ):
            return self._calculate_timerange_min_max(
                time_now,
                last_timestamp,
                timeframe,
                calculation.timerange_min,
                calculation.timerange_max,
                get_time_unit_seconds(calculation.timerange_unit),
            )

        logger.error(
            "No Information about the input time ranges for the calculation in the configuration."
        )
        return None, None

    def _calculate_timerange(
        self,
        time_now: datetime,
        last_timestamp: datetime,
        timeframe: timedelta,
        timerange_value: int,
        timerange_type: Union[TimerangeTypes, None],
        timerange_unit_factor: int,
    ) -> tuple[str, str]:
        """Function to calculate the timerange for the input data query based on a fixed timerange from the configuration

        Args:
            time_now (datetime): Time now
            last_timestamp (datetime): Timestamp of the last output
            timeframe (timerange): Timeframe between now and the last output in seconds
            timerange_value (int): Value of the timerange in the configuration
            timerange_type (str): Type of the timerange (absolute or relative)
            timerange_unit_factor (int): Factor to convert the time unit to seconds

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """
        if timerange_type is TimerangeTypes.ABSOLUTE:
            from_date = (
                time_now - timedelta(seconds=timerange_value * timerange_unit_factor)
            ).strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, None
        if timerange_type is TimerangeTypes.RELATIVE:
            if timeframe < timerange_value:
                from_date = (
                    time_now
                    - timedelta(seconds=timerange_value * timerange_unit_factor)
                ).strftime("%Y-%m-%dT%H:%M:%S%z")
                return from_date, None

            from_date = last_timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")
            to_date = (
                last_timestamp
                + timedelta(seconds=timerange_value * timerange_unit_factor)
            ).strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, to_date
        # Fallback to absolute if no type is specified
        from_date = (
            time_now - timedelta(seconds=timerange_value * timerange_unit_factor)
        ).strftime("%Y-%m-%dT%H:%M:%S%z")
        return from_date, None

    def _calculate_timerange_min_max(
        self,
        time_now: datetime,
        last_timestamp: datetime,
        timeframe: int,
        timerange_min: int,
        timerange_max: int,
        timerange_unit_factor: int,
    ) -> tuple[str, str]:
        """Function to calculate the timerange for the input data query based on a min and max timerange from the configuration

        Args:
            time_now (datetime): Time now
            last_timestamp (datetime): Timestamp of the last output
            timeframe (int): Timeframe between now and the last output in seconds
            timerange_min (int): Minimal value of the timerange in the configuration
            timerange_max (int): Maximal value of the timerange in the configuration
            timerange_unit_factor (int): Factor to convert the time unit to seconds

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """

        if timeframe < timerange_min:
            from_date = (
                (time_now - timedelta(seconds=timerange_min * timerange_unit_factor))
                .replace(tzinfo=tz.UTC)
                .strftime("%Y-%m-%dT%H:%M:%S%z")
            )
            return from_date, None
        if timeframe < timerange_max:
            from_date = last_timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, None

        from_date = last_timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")
        to_date = (
            last_timestamp + timedelta(seconds=timerange_max * timerange_unit_factor)
        ).strftime("%Y-%m-%dT%H:%M:%S%z")
        return from_date, to_date

    def _handle_calibration_method(self, last_timestamp: datetime) -> tuple[str, str]:
        """Funtion to calculate the dates for the calibration method

        Args:
            last_timestamp (datetime): Timestamp of the last output

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """
        calibration = (
            self.config.controller_settings.time_settings.calibration
        )  # input_data_timeranges.get("calibration", {})

        # TODO: How to handle the calibration time?
        timerange = calibration.get("timeoffset_hours")
        from_date = (last_timestamp - timedelta(hours=timerange)).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )
        to_date = last_timestamp

        return from_date, to_date

    def _get_last_timestamp_for_fiware_output(
        self, output_entity: OutputModel
    ) -> tuple[OutputDataEntityModel, Union[datetime, None]]:
        """
        Function to get the latest timestamps of the output entity from the FIWARE platform

        Args:
            output_entity (OutputModel): Output entity

        Returns:
            tuple[OutputDataEntityModel, Union[datetime, None]]: OutputDataEntityModel with timestamps for the attributes
                                                                 and the latest timestamp of the output entity for the attribute with the oldest value (None if no timestamp is available)
        """

        output_attributes_entity = self.cb_client.get_entity_attributes(
            entity_id=output_entity.id_interface
        )

        output_attributes_controller = {
            item.id_interface: item.id for item in output_entity.attributes
        }

        timestamps = []
        for attr in list(output_attributes_entity.keys()):
            if attr not in list(output_attributes_controller.keys()):
                continue
            if output_attributes_entity[attr].metadata.get("TimeInstant") is not None:
                timestamps.append(
                    OutputDataAttributeModel(
                        id=output_attributes_controller[attr],
                        latest_timestamp_output=datetime.strptime(
                            output_attributes_entity[attr]
                            .metadata.get("TimeInstant")
                            .value,
                            "%Y-%m-%dT%H:%M:%S.%f%z",
                        ),
                    )
                )

        if len(timestamps) > 0:
            timestamp_latest_output = min(
                [item.latest_timestamp_output for item in timestamps]
            )
        else:
            timestamp_latest_output = None

        return (
            OutputDataEntityModel(id=output_entity.id, attributes_status=timestamps),
            timestamp_latest_output,
        )


    def _get_last_timestamp_for_file_output(
        self, output_entity: OutputModel
    ) -> tuple[OutputDataEntityModel, Union[datetime, None]]:
        """
        Function to get the latest timestamps of the output entity from a File, if exitst

        Args:
            output_entity (OutputModel): Output entity

        Returns:
            tuple[OutputDataEntityModel, Union[datetime, None]]: OutputDataEntityModel with timestamps for the attributes
                                                                 and the latest timestamp of the output entity for the attribute with the oldest value (None if no timestamp is available)
        TODO:
            - is it really nessesary to get a timestamp for file-calculations -> during calculation time is set to input_time
        """
        
        output_id = output_entity.id_interface
        
     
       
        timestamps = []
        timestamp_latest_output = None

        return (
            OutputDataEntityModel(id=output_id, attributes_status=timestamps),
            timestamp_latest_output,
        )

    async def get_data(self, 
                       method: DataQueryTypes
                       ) -> InputDataModel:
        """
        Function to get the data of all input entities via the different interfaces (FIWARE, FILE, MQTT)
        Load Data from File: Be Carefull, it's the first value in the file.
        Args:
            method (DataQueryTypes): Method for the data query
        
        Returns:
            InputDataModel: Model with the input data


        TODO:
            - Implement the other interfaces(MQTT, ...)
            - Do we need this method parameter?
            - loading data from a file -> first/last/specifiv value in file
        """

        input_data = []
        context_data = []
        output_timestamps = []
        output_latest_timestamps = []


        if self.reload_contextdata or self.contextdata is None:
            logger.info("Loading of ConextData from config file")
            for context_entity in self.config.contextdata:
                
                if context_entity.interface == Interfaces.FIWARE:
        
                    context_data.append(
                        self.get_data_from_fiware(
                            method=method,
                            entity=context_entity,
                            timestamp_latest_output=output_latest_timestamp,
                        )
                    )

                if context_entity.interface == Interfaces.FILE:
                    
                    context_data.append(
                        self.get_contextdata_from_file(
                            method=method,
                            entity=context_entity,
                        )
                    )

                
                if context_entity.interface == Interfaces.MQTT:
                    logger.warning("interface MQTT for Contextdata not supported")
                
                self.contextdata = context_data


        for output_entity in self.config.outputs:
            
            if output_entity.interface == Interfaces.FIWARE:
                entity_timestamps, output_latest_timestamp = (
                    self._get_last_timestamp_for_fiware_output(output_entity)
                )  # TODO: What do we need, all of the timestamps or only the latest one?

                output_timestamps.append(entity_timestamps)
                output_latest_timestamps.append(output_latest_timestamp)

            elif output_entity.interface == Interfaces.FILE:
               
                entity_timestamps, output_latest_timestamp = (
                    self._get_last_timestamp_for_file_output(output_entity)
                )
                output_timestamps.append(entity_timestamps)
                output_latest_timestamps.append(output_latest_timestamp)
                logger.info("File interface, output_latest_timestamp is not defined.")

            elif output_entity.interface == Interfaces.MQTT:
                logger.warning("MQTT interface for output_entity not implemented yet.")
                raise NotSupportedError

        if len(output_latest_timestamps) > 0:
            output_latest_timestamp = min(output_latest_timestamps)
        else:
            output_latest_timestamp = None


        for input_entity in self.config.inputs:
            
            if input_entity.interface == Interfaces.FIWARE:

                input_data.append(
                    self.get_data_from_fiware(
                        method=method,
                        entity=input_entity,
                        timestamp_latest_output=output_latest_timestamp,
                    )
                )

            elif input_entity.interface == Interfaces.FILE:
                
                input_data.append(
                    self.get_data_from_file(
                        method=method,
                        entity=input_entity
                    )
                )
                              

            elif input_entity.interface == Interfaces.MQTT:
                logger.warning("MQTT interface for input_entity is not implemented yet.")
                raise NotSupportedError

            await sleep(0.1)

        return InputDataModel(
            input_entities=input_data, output_entities=output_timestamps, context_entities=self.contextdata
        )
    

    def get_data_from_file(
        self,
        method:DataQueryTypes,
        entity: InputModel,
        ) -> Union[InputDataEntityModel, None]:
        """
            Function to read input data for calculations from a input file.
            first step: read the first values in the file / id_inputs.  Then get the data from the entity since the last timestamp of the output entity from cratedb.
        Args:
            - method (DataQueryTypes): Keyword for type of query
            - entity (InputModel): Input entity
        TODO:
             - timestamp_latest_output (datetime): Timestamp of the input value
             -  -> seperating Data in Calculation or here ?? 
            
        Returns:
            - InputDataEntityModel: Model with the input data or None if the connection to the platform is not available

        """
         
        attributes_timeseries = {}
        attributes_values = []
        path_of_file = self.file_params["PATH_OF_INPUT_FILE"]
        time_format = self.file_params["TIME_FORMAT_FILE"]
        try:
            data = pd.read_csv(path_of_file, parse_dates=['Time'],sep=';',decimal=',')
            data.set_index('Time',inplace=True)
            data.index = pd.to_datetime(data.index, format = time_format)
            #time = self.file_params["START_TIME_FILE"]
            #temp = data.loc[time, 'outside_Temperature']
        except:
            print(f"Error: File not found ({path_of_file})")
        for attribute in entity.attributes:
                
                if attribute.type == AttributeTypes.TIMESERIES:
                    #attributes_timeseries[attribute.id] = attribute.id_interface
                    logger.warning(
                        f"Attribute type {attribute.type} for attribute {attribute.id} of entity {entity.id} not supported."
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
                        f"Attribute type {attribute.type} for attribute {attribute.id} of entity {entity.id} not supported."
                    )



        return InputDataEntityModel(id=entity.id, attributes=attributes_values)


    def get_data_from_fiware(
        self,
        method: DataQueryTypes,
        entity: InputModel,
        timestamp_latest_output: Union[datetime, None],
    ) -> Union[InputDataEntityModel, None]:
        """
        Function fetches the data for evaluation which have not yet been evaluated.
            First get the last timestamp of the output entity. Then get the data from the entity since the last timestamp of the output entity from cratedb.
        Args:
            - method (DataQueryTypes): Keyword for type of query
            - entity (InputModel): Input entity
            - timestamp_latest_output (datetime): Timestamp of the last output
            
        Returns:
            - InputDataEntityModel: Model with the input data or None if the connection to the platform is not available

        """

        attributes_timeseries = {}
        attributes_values = []

        try:
            fiware_input_entity_type = self.cb_client.get_entity(
                entity_id=entity.id_interface
            ).type
            fiware_input_entity_attributes = self.cb_client.get_entity_attributes(
                entity_id=entity.id_interface, entity_type=fiware_input_entity_type
            )
        except requests.exceptions.ConnectionError as err:
            logger.error(f"""No connection to platform (ConnectionError): {err}""")

            return None  # TODO: What to do if the connection is not available?

        for attribute in entity.attributes:

            if attribute.id_interface not in fiware_input_entity_attributes:
                logger.error(
                    f"Attribute {attribute.id_interface} not found in entity {entity.id_interface}"
                )

                continue  # TODO: What to do if the attribute is not found?

            if attribute.type == AttributeTypes.TIMESERIES:
                attributes_timeseries[attribute.id] = attribute.id_interface

            elif attribute.type == AttributeTypes.VALUE:
                attributes_values.append(
                    InputDataAttributeModel(
                        id=attribute.id,
                        data=fiware_input_entity_attributes[
                            attribute.id_interface
                        ].value,
                        data_type=AttributeTypes.VALUE,
                        data_available=True,
                        latest_timestamp_input=(fiware_input_entity_attributes[
                            attribute.id_interface
                        ].metadata.get("TimeInstant").value[:-1]).replace(tzinfo=tz.UTC),
                    )
                )
            else:
                logger.warning(
                    f"Attribute type {attribute.type} for attribute {attribute.id} of entity {entity.id} not supported."
                )

        if len(attributes_timeseries) > 0:
            attributes_values.extend(
                self.get_data_from_datebase(
                    entity_id=entity.id_interface,
                    entity_type=fiware_input_entity_type,
                    entity_attributes=attributes_timeseries,
                    method=method,
                    timestamp_latest_output=timestamp_latest_output,
                )
            )

        return InputDataEntityModel(id=entity.id, attributes=attributes_values)

    def get_data_from_datebase(
        self,
        entity_id: str,
        entity_type: str,
        entity_attributes: dict,
        method: DataQueryTypes,
        timestamp_latest_output: datetime,
    ) -> list[InputDataAttributeModel]:
        """
        Function to get the data from the database for the input attributes (crateDB is used)

        Args:
            - entity_id: id of the entity
            - entity_type: type of the entity
            - entity_attributes: dict with the attributes of the entity
            - method (DataQueryTypes): method of the function which queries the data (calculation or calibration)
            - timestamp_latest_output: timestamp of the last output of the entity

        Returns:
            - list of InputDataAttributeModel: list with the input attributes

        TODO:
            - Does it make sense to use the quantumleap client for this? https://github.com/RWTH-EBC/FiLiP/blob/master/filip/clients/ngsi_v2/quantumleap.py#L449
            - Improve the error handling
        """

        from_date, to_date = self._calculate_dates(
            method=method, last_timestamp=timestamp_latest_output
        )

        df = self.crate_db_client.get_data(
            service=self.fiware_params["service"],
            entity=entity_id,
            entity_type=entity_type,
            attributes=list(entity_attributes.values()),
            from_date=from_date,
            to_date=to_date,
            limit=200000,
        )

        if df.empty:
            logger.debug("Service has not received data from CrateDB")
            return None

        # resample the time series with configured time step size
        df.fillna(value=np.nan, inplace=True)
        time_step_seconds = int(
            self.config.controller_settings.time_settings.calculation.timestep
            * get_time_unit_seconds(
                self.config.controller_settings.time_settings.calculation.timestep_unit
            )
        )
        df = df.resample(f"""{time_step_seconds}s""").mean(numeric_only=True)

        input_attributes = []

        for attribute_id, attribute_id_interface in entity_attributes.items():
            df.rename(columns={attribute_id_interface: attribute_id}, inplace=True)
            data = df.filter([attribute_id]).dropna()
            if data.empty:
                logger.debug(
                    f"Data for attribute {attribute_id} of entity {entity_id} is empty"
                )
                input_attributes.append(
                    InputDataAttributeModel(
                        id=attribute_id,
                        data=None,
                        data_type=AttributeTypes.TIMESERIES,
                        data_available=False,
                        latest_timestamp_input=None,
                    )
                )
            else:
                logger.debug(
                    f"Service received data from CrateDB for attribute {attribute_id} of entity {entity_id}"
                )
                input_attributes.append(
                    InputDataAttributeModel(
                        id=attribute_id,
                        data=data,
                        data_type=AttributeTypes.TIMESERIES,
                        data_available=True,
                        latest_timestamp_input=to_date,
                    )
                )
        return input_attributes
    

    def get_contextdata_from_file(
        self,
        method:DataQueryTypes,
        entity: ContextDataModel,
        ) -> Union[InputDataEntityModel, None]:
        """
            Function to read context data for calculations from config file.
        Args:
            - method (DataQueryTypes): Keyword for type of query
            - entity (InputModel): Input entity
        TODO:
            - work with timeseries, for example: timetable with presence or heating_times
            - check if ContextDataEntityModel/ContextDataAttributeModel/ContextDataModel is nessesary
        Returns:
            - InputDataEntityModel: Model with the context data  

        """
         
        attributes_values = []

        
        for attribute in entity.attributes:
                
                if attribute.type == AttributeTypes.TIMESERIES:
                    #attributes_timeseries[attribute.id] = attribute.id_interface
                    logger.warning(
                        f"Attribute type {attribute.type} for attribute {attribute.id} of entity {entity.id} not supported."
                    )
                elif attribute.type == AttributeTypes.VALUE:
                    
                    attributes_values.append(
                        InputDataAttributeModel(
                            id=attribute.id,
                            data=attribute.value,
                            data_type=AttributeTypes.VALUE,
                            data_available=True,
                            latest_timestamp_input=None,
                        )
                    )
                else:
                    logger.warning(
                        f"Attribute type {attribute.type} for attribute {attribute.id} of entity {entity.id} not supported."
                    )



        return InputDataEntityModel(id=entity.id, attributes=attributes_values)


    def _get_output_entity_config(
        self,
        output_entity_id: str,
    ) -> Union[OutputModel, None]:
        """
        Function to get the configuration of the output attributes

        Args:
            - output_entity: id of the output entity

        Returns:
            - Union[OutputModel, None]: configuration of the output entity or None if the entity is not found
        """
        for entity in self.config.outputs:
            if entity.id == output_entity_id:
                return entity

        return None

    def _get_output_attribute_config(
        self,
        output_entity_id: str,
        output_attribute_id: str,
    ) -> Union[AttributeModel, None]:
        """
        Function to get the configuration of the output attribute

        Args:
            - output_entity: id of the output entity
            - output_attribute: id of the output attribute

        Returns:
            - Union[AttributeModel, None]: configuration of the output attribute or None if the attribute is not found
        """
        for entity in self.config.outputs:
            if entity.id == output_entity_id:

                for attribute in entity.attributes:
                    if attribute.id == output_attribute_id:
                        return attribute

        return None

    def _get_output_command_config(
        self,
        output_entity_id: str,
        output_command_id: str,
    ) -> Union[CommandModel, None]:
        """
        Function to get the configuration of the output attribute

        Args:
            - output_entity: id of the output entity
            - output_attribute: id of the output attribute

        Returns:
            - Union[AttributeModel, None]: configuration of the output attribute or None if the attribute is not found
        """
        for entity in self.config.outputs:
            if entity.id == output_entity_id:

                for commmand in entity.commands:
                    if commmand.id == output_command_id:
                        return commmand

        return None

    async def send_outputs(self,
                           data_output: Union[OutputDataModel, None]
                           ):
        """
        Send output data to the interfaces defined in the Config (FIWARE, MQTT, ?)

        Args:
            - data_output: OutputDataModel with the output data

        TODO:
            - Implement a way to use different interfaces (MQTT, ?)
        """

        if data_output is None:
            logger.debug("No data for sending to Fiware instance")
            return

        for output in data_output.entities:

            output_entity = self._get_output_entity_config(output_entity_id=output.id)
            output_attributes = []
            output_commands = []

            if output_entity is None:
                logger.debug(f"Output entity {output.id} not found in configuration.")
                continue

            for attribute in output.attributes:

                output_attribute = self._get_output_attribute_config(
                    output_entity_id=output.id, output_attribute_id=attribute.id
                )

                if output_attribute is None:
                    logger.debug(
                        f"Output attribute {attribute.id} not found in configuration."
                    )
                    continue

                output_attribute.value = attribute.value
                output_attribute.timestamp = attribute.timestamp
                output_attributes.append(output_attribute)

            for command in output.commands:

                output_command = self._get_output_command_config(
                    output_entity_id=output.id, output_command_id=command.id
                )

                if output_command is None:
                    logger.debug(
                        f"Output attribute {command.id} not found in configuration."
                    )
                    continue

                output_command.value = command.value
                output_commands.append(output_command)

            # TODO: Implement the sending of the data to the other interfaces (FILE, MQTT, ...)

            if output_entity.interface is Interfaces.FIWARE:

                self._send_data_to_fiware(
                    output_entity=output_entity,
                    output_attributes=output_attributes,
                    output_commands=output_commands,
                )

            elif output_entity.interface is Interfaces.FILE:
                logger.warning("File interface not implemented yet.")
                raise NotSupportedError

            elif output_entity.interface is Interfaces.MQTT:
                logger.warning("MQTT interface not implemented yet.")
                raise NotSupportedError
            
            await sleep(0.1)

        logger.debug("Finished sending output data")

    def _send_data_to_fiware(
        self,
        output_entity: OutputModel,
        output_attributes: list[AttributeModel],
        output_commands: list[CommandModel],
    ) -> None:
        """
        Function to send the output data to the FIWARE platform

        Args:
            - output_entity: OutputModel with the output entity
            - output_attributes: list with the output attributes
            - output_commands: list with the output commands

        TODO:
            - Maybe use parallel processing for the sending of the data
            - Is there a better way to send the data from dataframes to the FIWARE platform?
            - Could there be a problem with big dataframes --> so that the data is not sent to the FIWARE platform?
        """

        context_entity = self.cb_client.get_entity(output_entity.id_interface)

        entity_attributes = self.cb_client.get_entity_attributes(
            entity_id=context_entity.id, entity_type=context_entity.type
        )

        attrs = []
        for attribute in output_attributes:

            if attribute.id_interface in entity_attributes:
                datatype = entity_attributes[attribute.id_interface].type
            else:
                datatype = attribute.datatype

            if isinstance(attribute.value, pd.DataFrame):
                if len(attribute.value) == 0:
                    continue

                for index, row in attribute.value.iterrows():
                    meta_data = NamedMetadata(
                        name="TimeInstant",
                        type=DataType.DATETIME,
                        value=index.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    )

                    attrs.append(
                        NamedContextAttribute(
                            name=attribute.id_interface,
                            value=row[attribute.id],
                            type=datatype,
                            metadata=meta_data,
                        )
                    )

            else:

                meta_data = NamedMetadata(
                    name="TimeInstant",
                    type=DataType.DATETIME,
                    value=attribute.timestamp.strftime("%Y-%m-%dT%H:%M:%S%z"),
                )

                attrs.append(
                    NamedContextAttribute(
                        name=attribute.id_interface,
                        value=attribute.value,
                        type=datatype,
                        metadata=meta_data,
                    )
                )

        cmds = []
        for command in output_commands:
            cmds.append(
                NamedCommand(
                    name=command.id_interface,
                    value=command.value,
                    type=DataType.COMMAND,
                )
            )

        output_points = attrs + cmds

        self.cb_client.update_or_append_entity_attributes(entity_id=context_entity.id, entity_type=context_entity.type, attrs=output_points)

    async def _hold_sampling_time(
        self, start_time: datetime, hold_time: Union[int, float]
    ):
        """
        Wait in each cycle until the sampling time (or cycle time) is up. If the algorithm takes
        more time than the sampling time, a warning will be given.
        Args:
            start_time: datetime, start time of the cycle
            hold_time: int or float, sampling time in seconds
        """
        if ((datetime.now() - start_time).total_seconds()) > hold_time:
            logger.warning(
                "The processing time is longer than the sampling time. The sampling time must be increased!"
            )
        while ((datetime.now() - start_time).total_seconds()) < hold_time:
            await sleep(0.1)

        return

    async def calculation(
        self,
        data: InputDataModel,
    ) -> Union[DataTransferModel, None]:
        """
        Function to start the calculation, do something with data - used in the services

        Args:
            - data: InputDataModel with the input data
        Returns:
            - Union[DataTransferModell, None]: Output data from the calculation
        """
        # do the calculation
        data_output = None

        return data_output

    async def calibration(
        self, 
        data: InputDataModel):
        """
        Function to start the calibration, do something with data - used in the services
        """

        return None

    def prepare_output(self, data_output: DataTransferModel) -> OutputDataModel:
        """Function to prepare the output data for the different interfaces (FIWARE, FILE, MQTT) - Takes the data from the DataTransferModel and prepares the data for the output

        Args:
            data_output (DataTransferModell): DataTransferModel with the output data from the calculation

        Returns:
            OutputDataModel: OutputDataModel with the output data for the different interfaces
        """

        output_data = OutputDataModel(entities=[])
        logger.debug(self.config.outputs)
        output_attrs = {}
        output_cmds = {}
        logger.debug(data_output)
        for component in data_output.components:

            for output in self.config.outputs:

                if output.id == component.entity_id:

                    for attribute in output.attributes:

                        if attribute.id == component.attribute_id:

                            if output.id not in output_attrs:
                                output_attrs[output.id] = []

                            output_attrs[output.id].append(
                                AttributeModel(
                                    id=attribute.id,
                                    value=component.value,
                                    timestamp=component.timestamp,
                                )
                            )

                            break
                    for command in output.commands:

                        if command.id == component.attribute_id:

                            if output.id not in output_cmds:
                                output_cmds[output.id] = []

                            output_cmds[output.id].append(
                                CommandModel(id=command.id, value=component.value)
                            )

                            break

        for output in self.config.outputs:
            if output.id in output_attrs:
                attributes = output_attrs[output.id]
            else:
                attributes = []
            if output.id in output_cmds:
                commands = output_cmds[output.id]
            else:
                commands = []

            output_data.entities.append(
                OutputDataEntityModel(
                    id=output.id, attributes=attributes, commands=commands
                )
            )

        return output_data

    async def start_service(self):
        """
        Main function for converting the data
        """
        logger.info("Start the Service")

        while True:
            logger.debug("Start the Prozess")
            start_time = datetime.now()

            # we have to check the input type, if we need something from the config
            if self.config.interfaces.fiware :
                if self.fiware_token["authentication"] and (
                    self.fiware_token_client.check_token() is False
                ):
                    self.fiware_header.__dict__["authorization"] = (
                        self.fiware_token_client.baerer_token
                    )
            if self.config.interfaces.file:
                logger.debug("Maybe we have to set the start_time for the file here")
            

            data_input = await self.get_data(method=DataQueryTypes.CALCULATION)

            if data_input is not None:

                data_output = await self.calculation(data=data_input)

                data_output = self.prepare_output(data_output=data_output)

                await self.send_outputs(data_output=data_output)

            await self._set_health_timestamp()

            sampling_time = (
                self.config.controller_settings.time_settings.calculation.sampling_time
                * get_time_unit_seconds(
                    self.config.controller_settings.time_settings.calculation.sampling_time_unit
                )
            )
            await self._hold_sampling_time(
                start_time=start_time, hold_time=sampling_time
            )

    async def start_calibration(self):
        """
        Function for autonomous adjustment of the system parameters
        """

        if self.config.controller_settings.time_settings.calibration is None:
            logger.error(
                "No Information about the calibration time in the configuration."
            )
            return
        while True:
            logger.debug("Start Calibration")
            start_time = datetime.now()
            data_input = await self.get_data(method=DataQueryTypes.CALIBRATION)
            if data_input is not None and data_input["data_available"]:
                await self.calibration(df=data_input)
            else:
                logger.debug("No data available for calibration - skip calibration")

            sampling_time = (
                self.config.controller_settings.time_settings.calibration.sampling_time
                * get_time_unit_seconds(
                    self.config.controller_settings.time_settings.calibration.sampling_time_unit
                )
            )

            await self._hold_sampling_time(
                start_time=start_time, hold_time=sampling_time
            )

    async def check_health_status(self):
        """
        Function to check the health-status of the service
        """
        logger.debug("Start the the Health-Check")
        while True:

            start_time = datetime.now()
            sampling_time = (
                self.config.controller_settings.time_settings.calculation.sampling_time
                * get_time_unit_seconds(
                    self.config.controller_settings.time_settings.calculation.sampling_time_unit
                )
            )

            await update_health_file(
                time_cycle=sampling_time,
                timestamp_health=self.timestamp_health,
                timestamp_now=start_time,
            )

            await self._hold_sampling_time(start_time=start_time, hold_time=10)

    async def _set_health_timestamp(self):
        """
        Function to set the timestamp of the last health-check
        """
        self.timestamp_health = datetime.now()
        return
