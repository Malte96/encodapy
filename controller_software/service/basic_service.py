# Module for the basic service class for the data processing and transfer via different interfaces.
# TODO: The class is not yet finished and needs to be extended with the necessary functions and methods. It can not be used yet. -- Martin Altenburger
# Author: Martin Altenburger 
import json
import pandas as pd
import numpy as np
from asyncio import sleep
from datetime import datetime, timedelta, timezone
from dateutil import tz
from typing import Union
from loguru import logger
import requests
import multiprocessing
import concurrent.futures
from filip.clients.ngsi_v2 import ContextBrokerClient
from filip.models.base import DataType, FiwareHeaderSecure
from filip.models.ngsi_v2.base import NamedMetadata
from filip.models.ngsi_v2.context import NamedContextAttribute, ContextEntity
from fbs.software.utils import (
    update_health_file,
    get_env_variable,
    BaererToken,
    LoggerControl,
    CrateDBConnection,
    get_time_unit_seconds,
    TimeUnits)
from fbs.software.exceptions import NoCredentials
from IPython.display import display

from controller_software.config import ConfigModel, InputModel, OutputModel, Interfaces, AttributeTypes, TimerangeTypes
from controller_software.utils.models import InputDataModel, InputDataEntityModel, InputDataAttributeModel, OutputDataEntityModel, OutputDataAttributeModel

from controller_software.utils.error_handling import NotSupportedError

class ControllerBasicService():
    """
        Class for processing the measurement data including data transfer to a FIWARE platform.
            
    """
    def __init__(
        self,
        time_step:int = 10,
        sampling_time:int = 120,
        calibration_time:int = 600
    ) -> None:
        self.fiware_params = dict()
        self.database_params = dict()   
        self.fiware_token = dict()
        
        self.fiware_token_client = None
        self.fiware_header = None
        
        self.cb_client = None
        self.crate_db_client = None
        
        # TODO: How to handle the configuration of the timeranges and time steps
        self.time_step = time_step
        self.sampling_time = sampling_time
        self.calibration_time = calibration_time
        self.input_data_timeranges = dict()
        
        self.config = None
        
        self.logger = LoggerControl()

        self.timestamp_health = None
        

    
    async def _load_env(self):
        """
        Function loads the env of the service from the configuration file (.env).
            
        """
        self.fiware_params["cb_url"] = get_env_variable("CB_URL")
        self.fiware_params["service"] = get_env_variable("FIWARE_SERVICE")
        self.fiware_params["service_path"] = get_env_variable("FIWARE_SERVICE_PATH")
        self.fiware_token["authentication"] = get_env_variable("FIWARE_AUTH", type_variable="bool")
        if self.fiware_token["authentication"]:
            if get_env_variable("FIWARE_CLIENT_ID") is not None:
                self.fiware_token["client_id"] = get_env_variable("FIWARE_CLIENT_ID")
                self.fiware_token["client_secret"] = get_env_variable("FIWARE_CLIENT_PW")
                self.fiware_token["token_url"] = get_env_variable("FIWARE_TOKEN_URL")
            elif get_env_variable("FIWARE_BAERER_TOKEN") is not None:
                self.fiware_token["baerer_token"] = get_env_variable("FIWARE_BAERER_TOKEN")
            else:
                logger.error('No authentication credentials available')
                raise NoCredentials
        
         
        self.database_params["crate_db_url"] = get_env_variable("CRATE_DB_URL")
        self.database_params["crate_db_user"] = get_env_variable("CRATE_DB_USER")
        self.database_params["crate_db_pw"] = get_env_variable("CRATE_DB_PW")
        self.database_params["crate_db_ssl"] = get_env_variable("CRATE_DB_SSL", type_variable="bool")
        
        config_path = get_env_variable("CONFIG_PATH", type_variable="str", default_value=None)
            
        self.time_step = get_env_variable("TIME_STEP", type_variable="int")
        self.sampling_time = get_env_variable("SAMPLING_TIME", type_variable="int")
        self.calibration_time = get_env_variable("CALIBRATION_TIME", type_variable="int")
        
        # self.check_input_timeranges()
        
        logger.debug('Config succesfully loaded.')
        
        return config_path
    
    # async def _load_config_from_file(self,
    #                                  config_path:str
    #                                  )->None:
    #     """
    #     Function loads the configuration of the service from a file.
        
    #     Args:
    #         - config_path: path to the configuration file
    #     TODO:
    #         - Adjust the config for the possibility to use more than one input and output entity
    #         - Add a information about the type of needed data (time series or single values)
    #     """
    #     with open(config_path, 'r') as file:
    #         config = json.load(file)
            
    #     self.input_entity = config["input"]["entity_id"]
    #     self.output_entity = config["output"]["entity_id"]
    #     self.input_attributes = config["input"]["attributes"]
    #     self.output_attributes = config["output"]["attributes"]
        
    #     if "timeranges" in config.keys():
    #         self.input_data_timeranges = config["timeranges"]
    #     else:
    #         self.input_data_timeranges = get_env_variable("INPUT_DATA_TIMERANGES", type_variable="dict")
    
            
    async def prepare_basic_start(self):
        """
        Function to create important objects with the configuration from the configuration file (.env) and prepare the start basics of the service.
        
        TODO:
            - Implement the other interfaces(FILE, MQTT, ...)
            - How to handle the interfaces (FIWARE, FILE, MQTT), if they are not in use?
            
        """        
        config_path = await self._load_env()
        
        self.config = ConfigModel.from_json(file_path = config_path)
        
        if self.fiware_token["authentication"]:
            if "baerer_token" in self.fiware_token:
                self.fiware_token_client = BaererToken(token=self.fiware_token["baerer_token"])
            else:
                self.fiware_token_client = BaererToken(client_id=self.fiware_token["client_id"],
                                                       client_secret=self.fiware_token["client_secret"],
                                                       token_url=self.fiware_token["token_url"])
            self.fiware_header = FiwareHeaderSecure(service=self.fiware_params["service"],
                                                    service_path=self.fiware_params["service_path"],
                                                    authorization=self.fiware_token_client.baerer_token)
        else:
            self.fiware_header = FiwareHeaderSecure(service=self.fiware_params["service"],
                                                    service_path=self.fiware_params["service_path"])
            
        self.cb_client = ContextBrokerClient(url=self.fiware_params["cb_url"],
                                        fiware_header=self.fiware_header)
        
        self.crate_db_client = CrateDBConnection(crate_db_url=self.database_params["crate_db_url"],
                                                 crate_db_user=self.database_params["crate_db_user"],
                                                 crate_db_pw=self.database_params["crate_db_pw"],
                                                 crate_db_ssl=self.database_params["crate_db_ssl"])

        return
     
    async def prepare_start(self):
        """
        Function prepare the start of the service (calls the function for the basic preparing)
            
        """
        logger.info('Prepare Start of Service')
        
        await self.prepare_basic_start()   
       
   
    def _calculate_dates(self, 
                        method:str, 
                        last_timestamp:Union[datetime, None]
                        )-> tuple[str, str]:
        """Function to calculate the dates for the input data query

        Args:
            method (str): Method for the calculation
            time_now (datetime): Time now
            last_timestamp (datetime): Timestamp of the last output

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """
        
        time_now = datetime.now(timezone.utc)
        if last_timestamp is None:
            timeframe = 0
        else:
            timeframe = (time_now-last_timestamp).total_seconds() / 60
        from_date, to_date = None, None

        if method == "calculation":
            from_date, to_date = self._handle_calculation_method(time_now, last_timestamp, timeframe)
        elif method == "calibration":
            from_date, to_date = self._handle_calibration_method(last_timestamp)

        if to_date is None:
            to_date = time_now.strftime("%Y-%m-%dT%H:%M:%S%z")

        return from_date, to_date
    
    def _handle_calculation_method(self, 
                                   time_now:datetime,
                                   last_timestamp:datetime,
                                   timeframe:int,
                                   )-> tuple[str, str]:
        """Funtion to calculate the dates for the calculation method

        Args:
            time_now (datetime): Time now
            last_timestamp (datetime): Timestamp of the last output
            timeframe (timerange): Timeframe between now and the last output in seconds

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """
        calculation = self.config.controller_settings.timeranges.calculation

        if calculation.timerange is not None:
            return self._calculate_timerange(time_now, last_timestamp, timeframe, calculation.timerange, calculation.timerange_type, get_time_unit_seconds(calculation.timerange_unit))
        elif calculation.timerange_min is not None and calculation.timerange_max is not None:
            return self._calculate_timerange_min_max(time_now, last_timestamp, timeframe, calculation.timerange_min, calculation.timerange_max, get_time_unit_seconds(calculation.timerange_unit))
        else:
            logger.error("No Information about the input time ranges for the calculation in the configuration.")
            return None, None

    def _calculate_timerange(self,
                             time_now:datetime,
                             last_timestamp:datetime,
                             timeframe:timedelta,
                             timerange_value:int,
                             timerange_type:Union[TimerangeTypes, None],
                             timerange_unit_factor:int
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
            from_date = (time_now - timedelta(seconds=timerange_value * timerange_unit_factor)).strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, None
        elif timerange_type is TimerangeTypes.RELATIVE:
            if timeframe < timerange_value:
                from_date = (time_now - timedelta(seconds=timerange_value * timerange_unit_factor)).strftime("%Y-%m-%dT%H:%M:%S%z")
                return from_date, None
            else:
                from_date = last_timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")
                to_date = (last_timestamp + timedelta(seconds=timerange_value * timerange_unit_factor)).strftime("%Y-%m-%dT%H:%M:%S%z")
                return from_date, to_date
        else:  # Fallback to absolute if no type is specified
            from_date = (time_now - timedelta(seconds=timerange_value * timerange_unit_factor)).strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, None

    def _calculate_timerange_min_max(self,
                                     time_now:datetime,
                                     last_timestamp:datetime,
                                     timeframe:int,
                                     timerange_min:int,
                                     timerange_max:int,
                                     timerange_unit_factor:int
                                     )-> tuple[str, str]:
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
            from_date = (time_now - timedelta(seconds=timerange_min * timerange_unit_factor)).replace(tzinfo=tz.UTC).strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, None
        elif timeframe < timerange_max:
            from_date = last_timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, None
        else:
            from_date = last_timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")
            to_date = (last_timestamp + timedelta(seconds=timerange_max * timerange_unit_factor)).strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, to_date

    def _handle_calibration_method(self,
                                   last_timestamp:datetime
                                   )-> tuple[str, str]:
        """Funtion to calculate the dates for the calibration method

        Args:
            last_timestamp (datetime): Timestamp of the last output

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """
        calibration = self.config.controller_settings.timeranges.calibration  # input_data_timeranges.get("calibration", {})
        
        # TODO: How to handle the calibration time?
        timerange = calibration.get("timeoffset_hours")
        from_date = (last_timestamp - timedelta(hours=timerange)).strftime("%Y-%m-%dT%H:%M:%S%z")
        to_date = last_timestamp

        return from_date, to_date
    
    def _get_last_timestamp_for_fiware_output(self,
                                              output_entity: OutputModel
                                              )-> tuple[OutputDataEntityModel, Union[datetime, None]]:
        """
        Function to get the latest timestamps of the output entity from the FIWARE platform

        Args:
            output_entity (OutputModel): Output entity

        Returns:
            tuple[OutputDataEntityModel, Union[datetime, None]]: OutputDataEntityModel with timestamps for the attributes and the latest timestamp of the output entity (None if no timestamp is available)
        """
        
        output_attributes_entity = self.cb_client.get_entity_attributes(entity_id = output_entity.id_interface)
        
        output_attributes_controller = {item.id_interface: item.id for item in output_entity.attributes}

        timestamps = []
        for attr in list(output_attributes_entity.keys()):
            if attr not in list(output_attributes_controller.keys()):
                continue
            elif output_attributes_entity[attr].metadata.get("TimeInstant") is not None:
                timestamps.append(OutputDataAttributeModel(id=output_attributes_controller[attr],
                                                           latest_timestamp_output=output_attributes_entity[attr].metadata.get("TimeInstant")))
                

        if len(timestamps)>0:
            timestamp_latest_output = min([item.latest_timestamp_output for item in timestamps])
        else:
            timestamp_latest_output = None      
            
        return OutputDataEntityModel(id = output_entity.id,
                                     attributes=timestamps), timestamp_latest_output
            
    async def get_data(self,
                       method:str
                       ) -> InputDataModel:
        
        """
        Function to get the data of all input entities via the different interfaces (FIWARE, FILE, MQTT)        

        Returns:
            InputDataModel: Model with the input data
            
                
        TODO:
            - Implement the other interfaces(FILE, MQTT, ...)
            - Do we need this method parameter?
        """
        
        input_data = []
        output_timestamps = []
        output_latest_timestamps = []
        
        for output_entity in self.config.outputs:
            if output_entity.interface == Interfaces.FIWARE:
                entity_timestamps, output_latest_timestamp = self._get_last_timestamp_for_fiware_output(output_entity) # TODO: What do we need, all of the timestamps or only the latest one?

                output_timestamps.append(entity_timestamps)
                output_latest_timestamps.append(output_latest_timestamp)
            
            elif output_entity.interface == Interfaces.FILE:
                logger.warning("File interface not implemented yet.")
                raise NotSupportedError
            
            elif output_entity.interface == Interfaces.MQTT:
                logger.warning("MQTT interface not implemented yet.")
                raise NotSupportedError
        
        if len(output_latest_timestamps)>0:
            output_latest_timestamp = min(output_latest_timestamps)
        else:
            output_latest_timestamp = None
        
        
        for input_entity in self.config.inputs:
            
            if input_entity.interface == Interfaces.FIWARE:
                
                input_data.append(self.get_data_from_fiware(method=method, entity=input_entity, timestamp_latest_output = output_latest_timestamp))
            
            elif input_entity.interface == Interfaces.FILE:
                
                logger.warning("File interface not implemented yet.")
                raise NotSupportedError
            
            elif input_entity.interface == Interfaces.MQTT:
                logger.warning("MQTT interface not implemented yet.")
                raise NotSupportedError
            
            await sleep(0.1)
            
    
        return InputDataModel(input_entities=input_data, output_entities=output_timestamps)
                
        
    def get_data_from_fiware(self,
                             method:str,
                             entity:InputModel,
                             timestamp_latest_output:Union[datetime, None],
                             ) -> Union[dict, None]:
        """
        Function fetches the data for evaluation which have not yet been evaluated.
            First get the last timestamp of the output entity. Then get the data from the entity since the last timestamp of the output entity from cratedb.
        Args:
            - method: Keyword for type of query
            
        """
        
        attributes_timeseries = {}
        attributes_values = []
        
        
        try:
            fiware_input_entity_type = self.cb_client.get_entity(entity_id=entity.id_interface).type
            fiware_input_entity_attributes = self.cb_client.get_entity_attributes(entity_id=entity.id_interface, entity_type=fiware_input_entity_type)
        except requests.exceptions.ConnectionError as err:
            logger.error(f"""No connection to platform (ConnectionError): {err}""")
            
            return None # TODO: What to do if the connection is not available?
            
        for attribute in entity.attributes:
            
            if attribute.id_interface not in fiware_input_entity_attributes:
                logger.error(f"Attribute {attribute.id_interface} not found in entity {entity.id_interface}")
                
                continue # TODO: What to do if the attribute is not found?
            
            if attribute.type == AttributeTypes.TIMESERIES:
                attributes_timeseries[attribute.id] = attribute.id_interface
                
            elif attribute.type == AttributeTypes.VALUE:
                attributes_values.append(InputDataAttributeModel(data=fiware_input_entity_attributes[attribute.id_interface].value,
                                                                 data_type=AttributeTypes.VALUE,
                                                                 data_available=True,
                                                                 latest_timestamp_input=fiware_input_entity_attributes[attribute.id_interface].metadata.get("TimeInstant").value[:-1]).replace(tzinfo=tz.UTC))
            else:
                logger.warning(f"Attribute type {attribute.type} for attribute {attribute.id} of entity {entity.id} not supported.")
                
        
        if len(attributes_timeseries) > 0:
            attributes_values.extend(self.get_data_from_datebase(entity_id=entity.id_interface,
                                                                 entity_type=fiware_input_entity_type,
                                                                 entity_attributes=attributes_timeseries,
                                                                 method=method,
                                                                 timestamp_latest_output=timestamp_latest_output))
            
        return InputDataEntityModel(id=entity.id,
                                    attributes=attributes_values)
        
    def get_data_from_datebase(self,
                               entity_id:str,
                               entity_type:str,
                               entity_attributes:dict,
                               method:str,
                               timestamp_latest_output:datetime
                               )-> list[InputDataAttributeModel]:
        
        """
        Function to get the data from the database for the input attributes (crateDB is used)
        
        Args:
            - entity_id: id of the entity
            - entity_type: type of the entity
            - entity_attributes: dict with the attributes of the entity
            - method: method of the function which queries the data (calculation or calibration)
            - timestamp_latest_output: timestamp of the last output of the entity
            
        Returns:    
            - list of InputDataAttributeModel: list with the input attributes
        
        TODO:
            - Does it make sense to use the quantumleap client for this? https://github.com/RWTH-EBC/FiLiP/blob/master/filip/clients/ngsi_v2/quantumleap.py#L449
        """
        
        from_date, to_date = self._calculate_dates(method=method, last_timestamp=timestamp_latest_output)

        
        df = self.crate_db_client.get_data(service=self.fiware_params["service"], 
                                           entity=entity_id,
                                           entity_type=entity_type,
                                           attributes=list(entity_attributes.values()),
                                           from_date=from_date,
                                           to_date=to_date,
                                           limit=200000)   
        
        if df.empty:
            logger.debug('Service has not received data from CrateDB')
            return None
    
        # resample the time series with configured time step size
        df.fillna(value=np.nan, inplace=True)
        df = df.resample(f"""{self.time_step}s""").mean(numeric_only=True)
        
        
        input_attributes = []
        
        for attribute_id, attribute_id_interface in entity_attributes.items():
            data = df.filter([attribute_id_interface]).dropna()
            if data.empty:
                logger.debug(f"Data for attribute {attribute_id} of entity {entity_id} is empty")
                input_attributes.append(InputDataAttributeModel(id=attribute_id,
                                                                data=None,
                                                                data_type=AttributeTypes.TIMESERIES,
                                                                data_available=False,
                                                                latest_timestamp_input=None))
            else:
                logger.debug(f'Service received data from CrateDB for attribute {attribute_id} of entity {entity_id}')
                input_attributes.append(InputDataAttributeModel(id=attribute_id,
                                                                data=data,
                                                                data_type=AttributeTypes.TIMESERIES,
                                                                data_available=True,
                                                                latest_timestamp_input=to_date))
        return input_attributes         
            

    def push_data(self,
                  data_output: Union[dict, None],
                  timestamp_end_query_input: str
                  ):
        """
        Send output data to Fiware platform, using parallel executions
        
        Args:
            - data_output: dict with name and data as dataframe or null
            - timestamp_end_query_input: timestamp of end of input data query - useful to send null values, if there are no input values
        
        """
        
        if data_output is None:
            logger.debug("No data for sending to Fiware instance")
            return

        max_workers = multiprocessing.cpu_count()
        
        logger.debug(f"Start sending data to Fiware platform with {max_workers} workers.")
       
        context_entity = self.cb_client.get_entity(self.output_entity)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

            futures = []
       
            for key, data in data_output.items():
                logger.debug(f"Sending data with key {key}")
                        
                if isinstance(data, pd.DataFrame):
                    keys = data.columns.to_list()
                    
                    for index, row in data.iterrows():

                        if index is not None:
                            future = executor.submit(self.send_data, context_entity, keys, index, row.to_dict())
                            
                            futures.append(future)
                
                elif data is None and timestamp_end_query_input is not None:
                    future = executor.submit(self.send_null_data, context_entity, key, timestamp_end_query_input)
                    futures.append(future)
                else:
                    logger.warning(f"Only dataframes or None are supported as output data. Data with key {key} will not be sent to Fiware instance.")
                    pass 
                    

            concurrent.futures.wait(futures)

        logger.debug(f"Finished sending data to Fiware platform")

        return

    def send_data(self, 
                  context_entity: ContextEntity,
                  keys:Union[str, list],
                  time:datetime,
                  data:dict):
        try:           
            
            meta_data = NamedMetadata(name="TimeInstant", type=DataType.DATETIME, value=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
            attrs = []
            if isinstance(keys, list):
                for key in keys:
                    try:
                        context_attribute = context_entity.get_attribute(key)
                    except KeyError:
                        logger.error(f"Attribute {key} not found in entity {context_entity.id}")
                        continue
                    attrs.append(NamedContextAttribute(name=key, value=data[key], type=context_attribute.type, metadata=meta_data))

            else:
                attrs.append(NamedContextAttribute(name=keys, value=data[keys], type=context_entity.get_attribute(key).type, metadata=meta_data))
            self.cb_client.update_or_append_entity_attributes(entity_id=context_entity.id, entity_type=context_entity.type, attrs=attrs)

        except (KeyError, TypeError) as error:
            logger.error(f"Error while sending data for entity {context_entity.id}: {error}")

    def send_null_data(self, 
                       context_entity:ContextEntity,
                       keys:Union[str, list],
                       time:datetime):
        try:
            attrs = []
            if isinstance(keys, list):
                for key in keys:
                    meta_data = NamedMetadata(name="TimeInstant", type=DataType.DATETIME, value=time)
                    attrs.append(NamedContextAttribute(name=key, value=None, type=DataType.NUMBER, metadata=meta_data))
            elif isinstance(keys, str):
                meta_data = NamedMetadata(name="TimeInstant", type=DataType.DATETIME, value=time)
                attrs.append(NamedContextAttribute(name=keys, value=None, type=DataType.NUMBER, metadata=meta_data))
            else:
                logger.warning(f"Type of keys not supoerted will not be sent to Fiware instance.")
                pass
            self.cb_client.update_or_append_entity_attributes(entity_id=context_entity.id, entity_type=context_entity.type, attrs=attrs)

        except TypeError as error:
            logger.error(error)

    
    async def _hold_sampling_time(self, start_time: float, hold_time:int):
        """
        Wait in each cycle until the sampling time (or cycle time) is up. If the algorithm takes
        more time than the sampling time, a warning will be given.
        Args:
            start_time:
        """
        if ((datetime.now()-start_time).total_seconds()) > hold_time:
            logger.warning("The processing time is longer than the sampling time. The sampling time must be increased!")
        while ((datetime.now()-start_time).total_seconds()) < hold_time:
            await sleep(0.1)
        else:
            return
        
    async def calculation(self,
                          data:InputDataModel,
                          ):
        """
        Function to start the calculation, do something with data - used in the services 
        TODO: 
            - Adapt the function to the new configuration / input data model
        Args:
            - df: input dataframe
            - data_available: bool, if there are values in the dataframe
            - timestamp_last_output: Union[datetime, None] Time of last output of result in database, if available
        Returns:
            - dict with key and data - result like this: data_output = {self.output_attributes["dummy"]:pd.DataFrame()} or with None ( no values in input)
        """
        # do the calculation
        data_output = None
        
        return data_output
    
    async def calibration(self,
                          df:pd.DataFrame
                          ):
        """
        Function to start the calibration, do something with data - used in the services 
        """
        
        return None
    
     
    async def start_service(self):
        """
        Main function for converting the data 
        """
        logger.info('Start the Service')
        
        while True: 
            logger.debug('Start the Prozess')
            start_time = datetime.now()
            
            if self.fiware_token["authentication"] and (self.fiware_token_client.check_token() is False):
                self.fiware_header.__dict__['authorization'] = self.fiware_token_client.baerer_token
            
            data_input = await self.get_data(method="calculation")
            
            if data_input is not None:
            
                data_output = await self.calculation(data = data_input)

                # self.push_data(data_output = data_output, timestamp_end_query_input= data_input["timestamp_end_query_input"])
            
            await self._set_health_timestamp()
            await self._hold_sampling_time(start_time=start_time, hold_time = self.sampling_time * 60)
    
    async def start_calibration(self):
        """
        Function for autonomous adjustment of the system parameters
        """
        # await self._hold_sampling_time(start_time=datetime.now(), hold_time = self.calibration_time)
        
        if self.config.controller_settings.timeranges.calibration is None:
            logger.error("No Information about the calibration time in the configuration.")
            return
        while True:
            logger.debug('Start Calibration')
            start_time = datetime.now()
            data_input = await self.get_data(method="calibration")
            if data_input is not None and data_input["data_available"]:
                await self.calibration(df = data_input["data"])
            else:
                logger.debug("No data available for calibration - skip calibration")
            await self._hold_sampling_time(start_time=start_time, hold_time = self.calibration_time * 60 * 60)
            
    async def check_health_status(self):
        '''
        Function to check the health-status of the service
        '''
        logger.debug("Start the the Health-Check")
        while True:
            
            start_time = datetime.now()
            
            await update_health_file(time_cycle=self.sampling_time, timestamp_health=self.timestamp_health, timestamp_now=start_time)
            
            await self._hold_sampling_time(start_time=start_time, hold_time = 10)
            
    async def _set_health_timestamp(self):
        """
        Function to set the timestamp of the last health-check
        """
        self.timestamp_health = datetime.now()
        return