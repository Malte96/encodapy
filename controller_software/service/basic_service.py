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

from controller_software.config import ConfigModel, InputModel, OutputModel, Interfaces, AttributeTypes
from controller_software.utils.models import InputDataModel, InputDataEntityModel, InputDataAttributeModel, OutputDataEntityModel, OutputDataAttributeModel

from controller_software.utils.error_handling import NotSupportedError

class FiwareBasicService():
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
        self.fiware_token = dict()
        self.fiware_header = None
        self.cb_client = None
        self.crate_db_url = None
        self.crate_db_user = None
        self.crate_db_pw = None
        self.crate_db_ssl = None
        self.time_step = time_step
        self.sampling_time = sampling_time
        self.calibration_time = calibration_time
        self.input_entity = None
        self.output_entity = None
        self.input_attributes = dict()
        self.output_attributes = dict()
        self.logger = LoggerControl()
        self.input_data_timeranges = dict()
        self.timestamp_health = None
        

    
    async def _load_config_from_env(self):
        """
        Function loads the configuration of the service from the configuration file (.env).
            
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
            
        self.crate_db_url = get_env_variable("CRATE_DB_URL")
        self.crate_db_user = get_env_variable("CRATE_DB_USER")
        self.crate_db_pw = get_env_variable("CRATE_DB_PW")
        self.crate_db_ssl = get_env_variable("CRATE_DB_SSL", type_variable="bool")
        
        config_path = get_env_variable("CONFIG_PATH", type_variable="str", default_value=None)
            
        self.config = ConfigModel.from_json(file_path = config_path)
        

            
        self.time_step = get_env_variable("TIME_STEP", type_variable="int")
        self.sampling_time = get_env_variable("SAMPLING_TIME", type_variable="int")
        self.calibration_time = get_env_variable("CALIBRATION_TIME", type_variable="int")
        
        # self.check_input_timeranges()
        
        logger.debug('Config succesfully loaded.')
        
        return
    
    async def _load_config_from_file(self,
                                     config_path:str
                                     )->None:
        """
        Function loads the configuration of the service from a file.
        
        Args:
            - config_path: path to the configuration file
        TODO:
            - Adjust the config for the possibility to use more than one input and output entity
            - Add a information about the type of needed data (time series or single values)
        """
        with open(config_path, 'r') as file:
            config = json.load(file)
            
        self.input_entity = config["input"]["entity_id"]
        self.output_entity = config["output"]["entity_id"]
        self.input_attributes = config["input"]["attributes"]
        self.output_attributes = config["output"]["attributes"]
        
        if "timeranges" in config.keys():
            self.input_data_timeranges = config["timeranges"]
        else:
            self.input_data_timeranges = get_env_variable("INPUT_DATA_TIMERANGES", type_variable="dict")
    
    def check_input_timeranges(self):
        """
        Function to check the input timeranges and adjust them if necessary or raise an error if necessary information is missing.
        
        TODO: 
            - Updating the function for checking the complete configuration
        """
        assert "calculation" in self.input_data_timeranges, "No Information about the input time ranges for the calculation in the configuration."
        assert ("timedelta_min" in self.input_data_timeranges["calculation"] and 
                "timedelta_max" in self.input_data_timeranges["calculation"]) or "timedelta" in self.input_data_timeranges["calculation"], "No Information about the minimal or maximal input time range for the calculation in the configuration."

        
        if "calibration" not in self.input_data_timeranges:
            self.input_data_timeranges["calibration"] = {}
            if "timeoffset_hours" not in self.input_data_timeranges["calibration"]:
                if "timedelta_max" in self.input_data_timeranges["calculation"]:
                    self.input_data_timeranges["calibration"]["timeoffset_hours"] = self.input_data_timeranges["calculation"]["timedelta_max"]/60
                    logger.debug("No Information about the 'timeoffset_hours' for the calibration in the configuration. Using the maximal input time range for the calculation.")
                else:
                    if "timedelta_unit" in self.input_data_timeranges["calculation"]:
                        timedelta_unit_factor = get_time_unit_seconds(self.input_data_timeranges["calculation"]["timedelta_unit"])
                    else:
                        timedelta_unit_factor = None
                    if timedelta_unit_factor is None:
                        timedelta_unit_factor = get_time_unit_seconds("second")
                    self.input_data_timeranges["calibration"]["timeoffset_hours"] = self.input_data_timeranges["calculation"]["timedelta"]*timedelta_unit_factor/(60*60)
                    
    async def prepare_basic_start(self):
        """
        Function to create important objects with the configuration from the configuration file (.env) and prepare the start basics of the service.
            
        """        
        await self._load_config_from_env()
        
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
        
        self.crate_db_client = CrateDBConnection(crate_db_url=self.crate_db_url,
                                                 crate_db_user=self.crate_db_user,
                                                 crate_db_pw=self.crate_db_pw,
                                                 crate_db_ssl=self.crate_db_ssl)

        return
     
    async def prepare_start(self):
        """
        Function prepare the start of the service (calls the function for the basic preparing)
            
        """
        logger.info('Prepare Start of Service')
        
        await self.prepare_basic_start()   
       
   
    def _calculate_dates(self, 
                        method:str, 
                        last_timestamp:datetime
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
        timeframe = (time_now-last_timestamp).total_seconds() / 60
        timedelta_unit_factor = self._get_timedelta_unit_factor()
        from_date, to_date = None, None

        if method == "calculation":
            from_date, to_date = self._handle_calculation_method(time_now, last_timestamp, timeframe, timedelta_unit_factor)
        elif method == "calibration":
            from_date, to_date = self._handle_calibration_method(last_timestamp)

        if to_date is None:
            to_date = time_now.strftime("%Y-%m-%dT%H:%M:%S%z")

        return from_date, to_date
    
    def _get_timedelta_unit_factor(self)->int:
        """Function to get the factor for the time unit in seconds

        Returns:
            int: Faktor for the time unit in seconds
        """
        calculation = self.input_data_timeranges.get("calculation", {})
        timedelta_unit = calculation.get("timedelta_unit")
        if timedelta_unit:
            time_unit_factor = get_time_unit_seconds(timedelta_unit)
            if time_unit_factor is not None:
                return time_unit_factor
        logger.warning("No Information about the time unit for the calculation in the configuration. Using minutes as time unit.")
        return get_time_unit_seconds(TimeUnits.MINUTE.value) 
    
    def _handle_calculation_method(self, 
                                   time_now:datetime,
                                   last_timestamp:datetime,
                                   timeframe:int,
                                   timedelta_unit_factor:int
                                   )-> tuple[str, str]:
        """Funtion to calculate the dates for the calculation method

        Args:
            time_now (datetime): Time now
            last_timestamp (datetime): Timestamp of the last output
            timeframe (timedelta): Timeframe between now and the last output in seconds
            timedelta_unit_factor (int): Factor to convert the time unit to seconds

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """
        calculation = self.input_data_timeranges.get("calculation", {})
        timedelta_value = calculation.get("timedelta")
        timedelta_type = calculation.get("timedelta_type")
        timedelta_min = calculation.get("timedelta_min")
        timedelta_max = calculation.get("timedelta_max")

        if timedelta_value is not None:
            return self._calculate_timedelta(time_now, last_timestamp, timeframe, timedelta_value, timedelta_type, timedelta_unit_factor)
        elif timedelta_min and timedelta_max:
            return self._calculate_timedelta_min_max(time_now, last_timestamp, timeframe, timedelta_min, timedelta_max, timedelta_unit_factor)
        else:
            logger.error("No Information about the input time ranges for the calculation in the configuration.")
            return None, None

    def _calculate_timedelta(self,
                             time_now:datetime,
                             last_timestamp:datetime,
                             timeframe:timedelta,
                             timedelta_value:int,
                             timedelta_type:str,
                             timedelta_unit_factor:int
                             ) -> tuple[str, str]:
        """Function to calculate the timedelta for the input data query based on a fixed timedelta from the configuration

        Args:
            time_now (datetime): Time now
            last_timestamp (datetime): Timestamp of the last output
            timeframe (timedelta): Timeframe between now and the last output in seconds
            timedelta_value (int): Value of the timedelta in the configuration
            timedelta_type (str): Type of the timedelta (absolute or relative)
            timedelta_unit_factor (int): Factor to convert the time unit to seconds

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """
        if timedelta_type == "absolute":
            from_date = (time_now - timedelta(seconds=timedelta_value * timedelta_unit_factor)).strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, None
        elif timedelta_type == "relative":
            if timeframe < timedelta_value:
                from_date = (time_now - timedelta(seconds=timedelta_value * timedelta_unit_factor)).strftime("%Y-%m-%dT%H:%M:%S%z")
                return from_date, None
            else:
                from_date = last_timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")
                to_date = (last_timestamp + timedelta(seconds=timedelta_value * timedelta_unit_factor)).strftime("%Y-%m-%dT%H:%M:%S%z")
                return from_date, to_date
        else:  # Fallback to absolute if no type is specified
            from_date = (time_now - timedelta(seconds=timedelta_value * timedelta_unit_factor)).strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, None

    def _calculate_timedelta_min_max(self,
                                     time_now:datetime,
                                     last_timestamp:datetime,
                                     timeframe:int,
                                     timedelta_min:int,
                                     timedelta_max:int,
                                     timedelta_unit_factor:int
                                     )-> tuple[str, str]:
        """Function to calculate the timedelta for the input data query based on a min and max timedelta from the configuration

        Args:
            time_now (datetime): Time now
            last_timestamp (datetime): Timestamp of the last output
            timeframe (int): Timeframe between now and the last output in seconds
            timedelta_min (int): Minimal value of the timedelta in the configuration
            timedelta_max (int): Maximal value of the timedelta in the configuration
            timedelta_unit_factor (int): Factor to convert the time unit to seconds

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """
    
        if timeframe < timedelta_min:
            from_date = (time_now - timedelta(seconds=timedelta_min * timedelta_unit_factor)).replace(tzinfo=tz.UTC).strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, None
        elif timeframe < timedelta_max:
            from_date = last_timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, None
        else:
            from_date = last_timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")
            to_date = (last_timestamp + timedelta(seconds=timedelta_max * timedelta_unit_factor)).strftime("%Y-%m-%dT%H:%M:%S%z")
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
        calibration = self.input_data_timeranges.get("calibration", {})
        timeoffset_hours = calibration.get("timeoffset_hours", 0)
        from_date = (last_timestamp - timedelta(hours=timeoffset_hours)).strftime("%Y-%m-%dT%H:%M:%S%z")
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
        
        output_attributes_controller = {item["id_interface"]: item["id"] for item in output_entity.attributes}

        timestamps = []
        for attr in output_attributes_entity.keys():
            if attr not in output_attributes_controller.keys():
                continue
            elif output_attributes_entity[attr].metadata.get("TimeInstant") is not None:
                timestamps.append(OutputDataAttributeModel(id=output_attributes_controller[attr],
                                                           latest_timestamp_output=output_attributes_entity[attr].metadata.get("TimeInstant")))
                
          
        if len(timestamps.keys())>0:
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
        
        
        if len(output_latest_timestamps.keys())>0:
            output_latest_timestamp = min(output_latest_timestamps.values())
        else:
            output_latest_timestamp = None
        
        
        for input_entity in self.config.inputs:
            
            if input_entity.interface == Interfaces.FIWARE:
                
                input_data.append(self.get_data_from_fiware(method=method, entity=self.config.inputs[input_entity], timestamp_latest_output = output_latest_timestamp))
            
            elif input_entity.interface == Interfaces.FILE:
                
                logger.warning("File interface not implemented yet.")
                raise NotSupportedError
            
            elif input_entity.interface == Interfaces.MQTT:
                logger.warning("MQTT interface not implemented yet.")
                raise NotSupportedError
            
            await sleep(0.1)
            
    
        return InputDataModel(input_entitys=input_data, output_entitys=output_timestamps)
                
        
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
                                                                 entity_attributes=list(attributes_timeseries.values()),
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
        logger.debug('Service received data from CrateDB')
        
        input_attributes = []
        
        for attribute_id, attribute_id_interface in entity_attributes.items():
            data = df.filter([attribute_id_interface]).dropna()
            if data.empty:
                input_attributes.append(InputDataAttributeModel(id=attribute_id,
                                                                data=None,
                                                                data_type=AttributeTypes.TIMESERIES,
                                                                data_available=False,
                                                                latest_timestamp_input=None))
            else:
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
                          df:pd.DataFrame,
                          data_available:bool,
                          timestamp_last_output:Union[datetime, None],
                          ):
        """
        Function to start the calculation, do something with data - used in the services 
        Args:
            - df: input dataframe
            - data_available: bool, if there are values in the dataframe
            - timestamp_last_output: Union[datetime, None] Time of last output of result in database, if available
        Returns:
            - dict with key and data - result like this: data_output = {self.output_attributes["dummy"]:pd.DataFrame()} or with None ( no values in input)
        """
        if data_available:
            # do the calculation
            data_output = None
        else:
            # create values instead / or use None
            data_output = {}
            for output_attribut in self.output_attributes:
                data_output[self.output_attributes[output_attribut]] = None
        
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
            
                data_output = await self.calculation(df = data_input["data"], data_available=data_input["data_available"], timestamp_last_output = data_input["timestamp_last_output"])

                # self.push_data(data_output = data_output, timestamp_end_query_input= data_input["timestamp_end_query_input"])
            
            await self._set_health_timestamp()
            await self._hold_sampling_time(start_time=start_time, hold_time = self.sampling_time * 60)
    
    async def start_calibration(self):
        """
        Function for autonomous adjustment of the system parameters
        """
        # await self._hold_sampling_time(start_time=datetime.now(), hold_time = self.calibration_time)
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