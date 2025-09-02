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


# TODO: not in use
class OpenCEM_RTU_client:
    """
    creates a global RTU Client for OpenCEM. There can only be one client globally.
    If there already exist a smartGridready, put it as keyword argument global_client = client.

    """
    
    OpenCEM_global_RTU_client = None

    def __init__(self, port: str, baudrate: int, parity: str, client_timeout: int, *,
                 global_client=None):  # global_client:if there already exist a SmartGridready client it can be put here
        # if there does not exist a SmartGridready client
        if global_client is None:
            if OpenCEM_RTU_client.OpenCEM_global_RTU_client is None:
                self.client = ModbusSerialClient(method="rtu", port=port, parity=parity,
                                                 baudrate=baudrate, timeout=client_timeout)
                self.client.connect()
            else:
                self.client = OpenCEM_RTU_client.OpenCEM_global_RTU_client
        # if there is a smartGridReady client
        else:
            OpenCEM_RTU_client.OpenCEM_global_RTU_client = global_client
            self.client = global_client

    def get_OpenCEM_global_RTU_client(self):
        if self.client is not None:
            return self.client
        else:
            raise NotImplementedError

  
class SmartGridreadyComponent:  # TODO: check with new sgr_library
    # class for component with smartgridready compatibility

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
        
    async def read_value_with_conversion(self, functional_profile: str, data_point: str):
        # read a power or energy value with unit conversion to kW, kWh

        [value, unit, error_code] = await self.read_value(functional_profile, data_point)
        if unit.upper() == 'W' or unit.upper() == 'WATT' or unit.upper() == 'WATTS':
            value = value / 1000  # convert W to kW
            unit = "KILOWATT"  # change output unit to kW
        if unit.upper() == 'WH' or unit.upper() == 'WATT HOURS' or unit.upper() == 'WATTHOURS' or unit.upper() == "WATT_HOURS":
            value = value / 1000  # convert Wh to kWh
            unit = "KILOWATT_HOURS"  # change output unit to kWh

        return [round(value, 4), unit, error_code]  # value gets rounded

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
        self.dp_list = dp_list  # list of data points
      

        self.state = 0
        self.value = 0
        self.unit = None
        self.error_code = 0


        print(f"Device created: {self.name} type {self.type}")


    async def connect(self,smartGridreadyEID, param):
            print("Connecting to SmartGridready Component...")
            self.smartgridready_Comp = SmartGridreadyComponent()
            await self.smartgridready_Comp.connect(smartGridreadyEID, param)
            print(f"SmartGridready Component initialized: {smartGridreadyEID}")



    async def read(self):
        
        self.value = 0
        self.unit = 0
        self.error_code = 0
        self.dp = None
        self.datapoint_values = []
        print(self.dp_list)
        for dp_entry in self.dp_list: 
           
            fp = dp_entry['fp']
            dp = dp_entry['dp']

            #print(f"Reading data point: {fp}, {dp}")
            try:
                [value, unit, error_code] = await self.smartgridready_Comp.read_value(fp, dp)
                
                # Store individual datapoint information
                dp_info = {
                    'fp': fp,
                    'dp': dp,
                    'value': value,
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
        #print(f"Device read: {self.name} value {self.value:.2f} unit {self.unit} error code {self.error_code}")
        return self.datapoint_values#self.value, self.unit, self.error_code

        
        #pass
    def write_device_setpoint(self, functional_profile: str, setpoint: float):
        return 0        # error code

    def log_value_state(self, info: str = ""):
        # logs the data of a device.
        logger = logging.getLogger("device_logger")
        logger.info("test")
            # TODO #f"{self.name};{self.type};{info};{self.state};{self.value:.2f};{self.unit};{self.error_code}")

class CommunicationChannel: # TODO: check this
    # base class to describe a communication channel
    def __init__(self, type, param):
        self.type = type

        # decision tree for CommunicationChannel type
        match self.type:


            case "MODBUS_TCP":  # TODO: remove or still required?
                """
                address = param["address"]
                port = param["port"]
                self.client = AsyncModbusTcpClient(host=address, port=port)
                #evtl Routeradresse
                #ethernet port
                """
                pass


            case "MODBUS_RTU":
                port = param["port"]
                baudrate = param["baudrate"]
                match param["parity"]:
                    case "EVEN":
                        parity = "E"
                    case "ODD":
                        parity = "O"
                    case "NONE":
                        parity = "N"
                    case _:
                        raise NotImplementedError("Parity must be NONE,ODD or EVEN")

                #self.client = AsyncModbusSerialClient(method="rtu", port=port, baudrate=baudrate, parity=parity)
            case "HTTP_LOCAL":
                self.client = None
            case "SHELLY_CLOUD":
                self.client = None
                self.shelly_auth_key = param["authKey"]
                self.shelly_server_address = param["serverAddress"]
            case "SMARTME_CLOUD":
                self.client = None
                self.shelly_auth_key = param["authKey"]
                self.shelly_server_address = param["serverAddress"]
            case "REST_API":

                if param["AuthenticationMethod"] == "BearerSecurityScheme":
                    print("CommunicationChannel...case RESTAPI...BearerSecurityScheme")
                    """
                    headers = {
                        "Accept": "application/json",
                        "Content-Type": "application/json",

                    }
                    payload1 = json.dumps(str(self.config['configuration'][3]['authentication']['BearerSecurity']['Body']))

                    token = requests.request(
                    str(self.config['configuration'][3]['authentication']['BearerSecurity']['Method']),
                    str(self.config['configuration'][1]['TCP/IPUri']) + str(
                        self.config['configuration'][3]['authentication']['BearerSecurity']['EndPoint']),
                    headers=headers, data=payload1)
                    print("token")
                    print(token)
                    """

                elif param["AuthenticationMethod"] == "BasicSecurityScheme":
                    print("CommunicationChannel...case RESTAPI...BasicSecurityScheme")
                    self.baseURL = param["baseURL"]
                    self.username = param["username"]
                    self.password = param["password"]

            case "Lehmann":
                self.username = param["username"]
                self.password = param["password"]


            # general http client for the OpenCEM (for communication with GUI, etc.)
            case "HTTP_MAIN":
                self.client = aiohttp.ClientSession()
                pass
            case _:
                raise NotImplementedError(f"Communication {type} not known.")
