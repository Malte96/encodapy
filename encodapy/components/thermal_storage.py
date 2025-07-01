"""
Simple Method to caluculate the energy in a the thermal storage
Author: Martin Altenburger
"""
from typing import Union, Optional
from pandas import DataFrame, Series
import numpy as np
from encodapy.components.thermal_storage_config import (
    ThermalStorageTemperatureSensors,
    TemperatureLimits,
    TemperatureSensorValues)
from encodapy.utils.mediums import(
    Medium,
    get_medium_parameter)

class ThermalStorage():
    """
    Class to calculate the energy in a thermal storage.
    
    Args:
        sensor_config (ThermalStorageTemperatureSensors): \
            Configuration of the temperature sensors in the thermal storage
        volume (float): Volume of the thermal storage in m³
        medium (Medium): Medium in the thermal storage, e.g. water 
    
    """
    def __init__(self,
                 sensor_config: ThermalStorageTemperatureSensors,
                 volume:float,
                 medium:Medium
                 ) -> None:
        self.sensor_config = ThermalStorageTemperatureSensors.model_validate(sensor_config)

        self.volume = float(volume)

        self.sensor_volumes = self._calculate_volume_per_sensor()

        self.medium = medium

        self.sensor_values = None

    def _calculate_volume_per_sensor(self) -> dict:
        """
        Function to calculate the volume per sensor in the thermal storage

        Returns:
            dict: Volume per sensor in the thermal storage in m³
        """
        sensor_names = []
        sensor_heights = []

        sensor_volumes = {}

        old_height = 0
        for field_name, value in self.sensor_config:

            if "name" in field_name and value is not None:
                sensor_names.append(value)

            elif "height" in field_name and value is not None:
                sensor_heights.append(value)

        old_height = 0
        for index, sensor in enumerate(sensor_names):
            if index == len(sensor_names)-1:
                new_height = 100
            else:
                new_height = (sensor_heights[index] + sensor_heights[index+1])/2

            sensor_volumes[sensor] = (new_height - old_height)/100 * self.volume

            old_height = new_height


        return sensor_volumes

    def _get_sensor_volume(self,
                           sensor:str) -> float:
        """
        Function to get the volume of the sensors in the thermal storage

        Returns:
            float: Volume of the sensors in the thermal storage in m³
        """

        return round(self.sensor_volumes[sensor],3)

    def _get_sensor_limits(self,
                           sensor:str) -> TemperatureLimits:
        """
        Function to get the temperature limits of the sensors in the thermal storage
        Args:
            sensor (str): Name of the sensor in the thermal storage
        Returns:
            TemperatureLimits: Temperature limits of the sensors in the thermal storage
        """
        sensor_id = str(sensor.split("_")[1])

        for field_name, value in self.sensor_config:

            if "limits" in field_name and value is not None and sensor_id in field_name:
                return value

        return None

    def get_nominal_energy_content(self
                                   ) -> float:
        """
        Function to calculate the nominal energy content of the thermal storage

        Returns:
            float: Nominal energy content of the thermal storage in Wh
        """

        medium_parameter = get_medium_parameter(medium = self.medium)

        total_energy_calculator = 0
        for i in range(1, 6):
            sensor_name = getattr(self.sensor_config, f"sensor_{i}_name")

            if sensor_name is None:
                continue
            limits = self._get_sensor_limits(sensor_name)

            total_energy_calculator += ((limits.maximal_temperature
                                        - limits.minimal_temperature)
                                        * self._get_sensor_volume(sensor_name))

        return round(total_energy_calculator
                * medium_parameter.rho
                * medium_parameter.cp
                /3.6,2)
    def get_storage_energy_minimum(self) -> float:
        """
        Function to get the minimum energy content of the thermal storage

        Returns:
            float: Minimum energy content of the thermal storage in Wh
        """

        medium_parameter = get_medium_parameter(medium = self.medium)

        total_energy_calculator = 0
        for i in range(1, 6):
            sensor_name = getattr(self.sensor_config, f"sensor_{i}_name")

            if sensor_name is None:
                continue
            limits = self._get_sensor_limits(sensor_name)

            total_energy_calculator += ((limits.minimal_temperature
                                        - limits.reference_temperature)
                                        * self._get_sensor_volume(sensor_name))

        return round(total_energy_calculator
                * medium_parameter.rho
                * medium_parameter.cp
                /3.6,2)

    def get_storage_energy_maximum(self) -> float:
        """
        Function to get the maximum energy content of the thermal storage

        Returns:
            float: Maximum energy content of the thermal storage in Wh
        """
        medium_parameter = get_medium_parameter(medium = self.medium)

        total_energy_calculator = 0
        for i in range(1, 6):
            sensor_name = getattr(self.sensor_config, f"sensor_{i}_name")

            if sensor_name is None:
                continue

            limits = self._get_sensor_limits(sensor_name)

            total_energy_calculator += ((limits.maximal_temperature
                                        - limits.reference_temperature)
                                        * self._get_sensor_volume(sensor_name))

        return round(total_energy_calculator
                * medium_parameter.rho
                * medium_parameter.cp
                /3.6,2)

    def set_temperature_values(self,
                               temperature_values: dict
                               ) -> None:
        """
        Function to set the sensor values in the thermal storage

        Args:
            sensor_values (dict): Sensor values in the thermal storage \
                with the sensor names as keys
        """

        self.sensor_values = TemperatureSensorValues(
            sensor_1=temperature_values[self.sensor_config.sensor_1_name],
            sensor_2=temperature_values[self.sensor_config.sensor_1_name],
            sensor_3=temperature_values[self.sensor_config.sensor_1_name],
            sensor_4=temperature_values[self.sensor_config.sensor_4_name]
            if self.sensor_config.sensor_4_name is not None else None,
            sensor_5=temperature_values[self.sensor_config.sensor_5_name]
            if self.sensor_config.sensor_5_name is not None else None)

    def check_temperatur_of_highest_sensor(self,
                                           df:DataFrame,
                                           sensor_name:str,
                                           temperature_limits:TemperatureLimits,
                                           )-> Series:
        """
        Function to check if the temperature of the highest sensor is too low, \
            so there is no energy left
        Args:
            df (pd.DataFrame): DataFrame with temperature values and state of charge
            sensor_name (str): Name of the highest sensor / column in the dataframe
            temperature_limits (TemperatureLimits): Temperature Limits of the sensor

        Returns:
            pd.Series: Adjustested state of charge
        """
        ref_value = (
            temperature_limits.minimal_temperature
            + (temperature_limits.maximal_temperature  - temperature_limits.minimal_temperature
               ) * 0.1)
        df = df.copy()

        df["state_of_charge"] = np.where(
            df[sensor_name] < temperature_limits.minimal_temperature , 0,
            np.where(df[sensor_name] < ref_value,
                     (df[sensor_name] - temperature_limits.minimal_temperature )
                     /(temperature_limits.maximal_temperature
                       -temperature_limits.minimal_temperature),
                     df["state_of_charge"]))

        return df["state_of_charge"]

    def calculate_state_of_charge(self,
                                  input_data: Optional[Union[dict,
                                                             DataFrame,
                                                             TemperatureSensorValues
                                                             ]] = None
                                  )-> Union[float, DataFrame]:
        """
        Function to calculate the state of charge of the thermal storage

        If the temperature of the highest sensor is too low, there is no energy left.
        
        Args:
            input_data (Optional[Union[dict, DataFrame, TemperatureSensorValues]]): \
                Input data for the calculation of the state of charge of the thermal storage \
                    (temperature values of the sensors)

        Returns:
            Union[float, DataFrame]: State of charge of the thermal storage in percent (0-100) 
                / DataFrame with the state of charge if the input is a DataFrame
        """

        if input_data is None:
            input_data = self.sensor_values

        if isinstance(input_data, dict):
            df = DataFrame(input_data, index=[0])


        elif isinstance(input_data, TemperatureSensorValues):
            input_data_dict = {}
            for i in range (1, len(input_data.model_dump().keys()) + 1):
                input_data_dict[self.sensor_config.model_dump()
                                [f"sensor_{i}_name"]
                                ] = input_data.model_dump()[f"sensor_{i}"]

            df = DataFrame(input_data_dict, index=[0])

        else:
            df = input_data.copy()


        sensors = {}
        sensor_limits = {}
        for field_name, value in self.sensor_config:

            if "name" in field_name and value is not None:
                sensors[value] = self._get_sensor_volume(value)
                sensor_limits[value] = self._get_sensor_limits(field_name)

        df["state_of_charge"] = 0

        for sensor_name, sensor_volume in sensors.items():

            df["state_of_charge"] += ((df[sensor_name]
                                       - sensor_limits[sensor_name].minimal_temperature)
                                      /(sensor_limits[sensor_name].maximal_temperature
                                        - sensor_limits[sensor_name].minimal_temperature)
                                      * sensor_volume)

        df["state_of_charge"] = (df["state_of_charge"] / self.volume * 100).clip(lower=0)

        df["state_of_charge"]  = self.check_temperatur_of_highest_sensor(
            df = df,
            sensor_name=self.sensor_config.sensor_1_name,
            temperature_limits=sensor_limits[self.sensor_config.sensor_1_name]
        )

        if isinstance(input_data, dict) or isinstance(input_data, TemperatureSensorValues):
            return round(df["state_of_charge"].values[0],2)

        return df.filter(["state_of_charge"]).round(2)

    def get_energy_content(self,
                           state_of_charge: Union[float, None] = None
                           ) -> float:
        """
        Function to calculate the energy content of the thermal storage

        Args:
            state_of_charge (float): State of charge of the thermal storage in percent (0-100)

        Returns:
            float: Energy content of the thermal storage in Wh
        """
        if state_of_charge is None:
            if self.sensor_values is None:
                raise ValueError("Sensor values are not set. Please set the sensor values first")
            state_of_charge = self.calculate_state_of_charge(input_data = self.sensor_values)

        return round(state_of_charge/100
                * self.get_nominal_energy_content(),2)
