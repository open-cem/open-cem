"""
-------------------------------------------------------
cem_lib_components
Library for OpenCEM
Contains classes for devices
-------------------------------------------------------
Fachhochschule Nordwestschweiz, Institut für Automation
Authors: Prof. Dr. D. Zogg, S. Ferreira, Ch. Zeltner
Version: 2.0, October 2024
-------------------------------------------------------
"""


import asyncio
import json
import logging
import math

import aiohttp
import time
#from audioop import mul
from operator import truediv
from pprint import pprint

import requests
from pymodbus.constants import Endian

import random
import sys, os
from datetime import datetime, timedelta


# pymodbus
from pymodbus.client import ModbusSerialClient, AsyncModbusTcpClient, AsyncModbusSerialClient


from datetime import datetime

from sgr_commhandler.device_builder import DeviceBuilder

# Simulation parameters:
simulation_speed_up_factor = 1  # will be overwritten by setting yaml
sim_start_time = None


  
class SmartGridreadyComponent:  
    

    def __init__(self):
        self.device = None

    async def connect(self, XML_file: str, EID_param: dict):
        print(f"SmartGridready Component connected: {XML_file} with EID {EID_param}")
        self.device = DeviceBuilder().eid_path(XML_file).properties(EID_param).build()
        await self.device.connect_async()
        


        


    async def read_value(self, functional_profile: str, data_point: str):
        # read one value from a given data point within a functional profile
        
        error_code = 0
        print(f"SmartGridready Component read value: {functional_profile, data_point}")
        #dp = self.device.get_functional_profile(functional_profile).get_data_point(data_point)
        dp = self.device.get_data_point((functional_profile,data_point ))
        value = await dp.get_value_async()
        
        unit = dp.unit().name
        return [value, unit, error_code]
        
    def write_value(self, functional_profile: str, data_point: str, value):
        # write one value to a given data point within a functional profile

        error_code = 0
        dp = self.device.get_data_point((data_point, functional_profile))

        
        #self.sgr_component.setval(functional_profile, data_point, value)

        print(f"SmartGridready Component write value: {functional_profile, data_point, value}")

        return error_code



class Device():
    # base class for any device including sensors and actuators

    def __init__(self, *, name: str = "", type: str = "", smartGridreadyEID: str = "", EID_param: str ="", 
                 isLogging: bool = True,
                
                 param: dict = {},
                 dp_list: list = None
                 ):

        self.name = name
        self.type = type
        self.smartGridreadyEID = smartGridreadyEID
        self.EID_param = EID_param

        self.isLogging = isLogging
  
        
        self.param = param
        self.dp_list = dp_list  


        print(f"Device created: {self.name} type {self.type}")


    async def connect(self,smartGridreadyEID, param):
            print("Connecting to SmartGridready Component...")
            self.smartgridready_Comp = SmartGridreadyComponent()
            await self.smartgridready_Comp.connect(smartGridreadyEID, param)
            print(f"SmartGridready Component initialized: {smartGridreadyEID}")



    async def read(self):
        self.datapoint_values = []
        
        for dp_entry in self.dp_list: 
           
            fp = dp_entry['fp']
            dp = dp_entry['dp']

            
            try:
                [self.value, unit, error_code] = await self.smartgridready_Comp.read_value(fp, dp)
                
                # Store individual datapoint information
                dp_info = {
                    'fp': fp,
                    'dp': dp,
                    'value': self.value,
                    'unit': unit,
                    'error_code': error_code
                }
                print("Device read", self.value, unit, error_code    )
                self.datapoint_values.append(dp_info)
                
            except Exception as e:
                print(f"Error reading datapoint {fp}/{dp}: {e}")
                
                # Store error information
                dp_info = {
                    'fp': fp,
                    'dp': dp,
                    'value': 0,
                    'unit': 'ERROR',
                    'error_code': 1
                }
                self.datapoint_values.append(dp_info)
        print("Device read", self.datapoint_values)       
        
        return self.datapoint_values

        
        #pass
    def write_device_setpoint(self, functional_profile: str, setpoint: float):
        return 0        # error code

    