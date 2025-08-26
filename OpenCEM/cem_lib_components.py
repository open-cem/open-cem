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
#from sgr_library import SGrDevice
from OpenCEM.native_device import NativeDevice

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
        print(EID_param)
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

    

    

class NativeComponent:  # TODO: implement this
    # class for component with native implementation
    # real components without a working XML-file

    def __init__(self, YAML_file: str, params: dict):

        interface_file = YAML_file
        print(params)
        self.native_component = NativeDevice(interface_file)
        self.native_component.update_yaml(params)
        self.native_component.connect()

        print(f"Native Component created: {YAML_file}")


    async def read_value(self, data_point: str):
        # read one value from a given data point within a functional profile
        error_code = 0
        value, unit,error_code = self.native_component.read_Value(data_point)

        # TODO: add code here - read value from data_point



        print(f"Native Component value read: {value}")

        return [value, unit, error_code]

    async def read_value_with_conversion(self, data_point: str):   #async def read_value_with_conversion(self, functional_profile: str,data_point: str):
        # read a power or energy value with unit conversion to kW, kWh

        [value, unit, error_code] = await self.read_value( data_point)
        if unit.upper() == 'W' or unit.upper() == 'WATT' or unit.upper() == 'WATTS':
            value = value / 1000  # convert W to kW
            unit = "KILOWATT"  # change output unit to kW
        if unit.upper() == 'WH' or unit.upper() == 'WATT HOURS' or unit.upper() == 'WATTHOURS' or unit.upper() == "WATT_HOURS":
            value = value / 1000  # convert Wh to kWh
            unit = "KILOWATT_HOURS"  # change output unit to kWh

        return [round(value, 4), unit, error_code]  # value gets rounded

    def write_value(self, data_point: str, value):
        # write one value to a given data point within a functional profile

        error_code = 0

        # TODO: add code here - write value to data point
        value = 0
        unit = None

        print(f"Native Component value write: {value} unit {unit}")

        return error_code


class Device():
    # base class for any device including sensors and actuators

    def __init__(self, *, name: str = "", type: str = "", smartGridreadyEID: str = "", nativeEID: str = "", EID_param: str ="",
                 simulationModel: str = "", 
                 isLogging: bool = True,
                 communicationChannel: str = "",
                 param: dict = {},
                 dp_list: list = None
                 ):

        self.name = name
        self.type = type
        self.smartGridreadyEID = smartGridreadyEID
        self.EID_param = EID_param

        self.nativeEID = nativeEID
        self.simulationModel = simulationModel
        self.isLogging = isLogging
        self.communicationChannel = communicationChannel
        
        self.param = param
        self.dp_list = dp_list  # list of data points
        self.nominalPower = 0

        self.state = 0
        self.value = 0
        self.unit = None
        self.error_code = 0


        if nativeEID != "None":
            self.native = NativeComponent(nativeEID, self.param)

        print(f"Device created: {self.name} type {self.type}")


    async def connect(self,smartGridreadyEID, param):
            print("Connecting to SmartGridready Component...")
            self.smartgridready_Comp = SmartGridreadyComponent()
            await self.smartgridready_Comp.connect(smartGridreadyEID, param)
            print(f"SmartGridready Component initialized: {smartGridreadyEID}")



    async def read(self):
        pass


    def write_device_setpoint(self, functional_profile: str, setpoint: float):
        return 0        # error code

    def log_value_state(self, info: str = ""):
        # logs the data of a device.
        logger = logging.getLogger("device_logger")
        logger.info("test")
            # TODO #f"{self.name};{self.type};{info};{self.state};{self.value:.2f};{self.unit};{self.error_code}")


class PowerSensor(Device):
    # derived class for power sensor
    #sleep_between_requests = 0.05

    def __init__(self, *, name: str = "", type: str = "",
                 smartGridreadyEID: str = "",
                 EID_param: str = "",
                 nativeEID: str = "",
                 simulationModel: str = "",
                 isLogging: bool = True,
                 communicationChannel: str = "",
                 param: dict = None,
                 dp_list : list = None
                 
                 ):

        # initialize sensor
        super().__init__(name=name, type=type, smartGridreadyEID=smartGridreadyEID, EID_param=EID_param, nativeEID=nativeEID,
                         simulationModel=simulationModel, isLogging=isLogging, communicationChannel=communicationChannel, param= param, dp_list=dp_list)

       
        if param is None:
            param = {}


    async def read_power(self):
        """
        returns the total power of a powersensor in kW. For not SmartGridReady devices you need to add_RTU_Power_entry() first.
        :returns: the power value, the unit, and error code
        """
        self.value = 0
        self.unit = 0
        self.error_code = 0
        self.dp = None
        self.datapoint_values = []
        for dp_entry in self.dp_list:  # self.dp_list is your loaded datapoints list
            fp = dp_entry['fp']
            dp = dp_entry['dp']

            print(f"Reading data point: {fp}, {dp}")
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
        
       
        

        """
        if self.smartGridreadyEID != "None":
            print("datapoint reading")
            print(self.dp_list)
            for dp_entry in self.dp_list:  # self.dp_list is your loaded datapoints list
                fp = dp_entry['fp']
                self.dp = dp_entry['dp']

                print(f"Reading data point: {fp}, {self.dp}")
                [self.value, self.unit, self.error_code] = await self.smartgridready_Comp.read_value(fp, self.dp)
        """    


        if self.nativeEID != "None":
            [self.value, self.unit, self.error_code] = await self.native.read_value('ActivePowerACtot')


        
        print(f"Power sensor read power: {self.name} value {self.value:.2f} unit {self.unit} error code {self.error_code}")

        return self.value, self.unit, self.error_code

    async def get_power(self):
        return self.value, self.unit, self.error_code

    

    

    async def get_energy_export(self):
        return self.energy_value_export

    async def read(self):
        await self.read_power()

class TemperatureSensor(Device):
    # derived class for temperature sensor

    def __init__(self, *, name: str = "", type: str = "",
                 smartGridreadyEID: str = "",
                 EID_param: str = "",
                 nativeEID: str = "",
                 simulationModel: str = "",
                 isLogging: bool = True,
                 communicationChannel: str = "",
                 address: str = "",
                 maxTemp: int, minTemp: int):

        # initialize sensor
        super().__init__(name=name, type=type, smartGridreadyEID=smartGridreadyEID, EID_param=EID_param, nativeEID=nativeEID,
                         simulationModel=simulationModel, isLogging=isLogging, communicationChannel=communicationChannel)
        self.address = address
        self.maxTemp = maxTemp
        self.minTemp = minTemp
        self.value = 0

        

        if self.error_code == 0:
            if self.value > self.maxTemp:
                self.value = self.maxTemp
            if self.value < self.minTemp:
                self.value = self.minTemp
        if self.isLogging:
            self.log_value_state('read_temperature')

        print(f"Temperature sensor read temperature: {self.name} value {self.value:.2f} unit {self.unit} "
              f"error code {self.error_code}")

        return self.value, self.unit, self.error_code


    async def read(self):
        await self.read_temperature()

class RelaisActuator(Device):
    # derived class for relais switch

    def __init__(self, *, name: str = "",
                 type: str = "",
                 smartGridreadyEID: str = "",
                 EID_param: str = "",
                 nativeEID: str = "",
                 simulationModel: str = "",
                 isLogging: bool = True,
                 communicationChannel: str = "",
                 address: str = "",
                 nChannels: int = 1):

        # initialize actuator
        super().__init__(name=name, type=type, smartGridreadyEID=smartGridreadyEID, EID_param=EID_param,
                         nativeEID=nativeEID,simulationModel=simulationModel, isLogging=isLogging,
                         communicationChannel=communicationChannel)
        self.address = address
        self.nChannels = nChannels

        #if simulationModel != None:
        #    self.simulation = SimulatedComponent(simulationModel, max_power=None, min_power=None, nominal_power=None,
        #                                         min_temperature=None, max_temperature=None)

    async def read_channel(self, channel: int):
        self.state = 0
        self.error_code = 0

        # TODO: specify fp and dp names
        fp_str = "SWITCH"
        dp_str = f"CHANNEL{channel}"

        if self.smartGridreadyEID != None:
            [self.state, self.error_code] = await self.smartgridready_Comp.read_value(fp_str, dp_str)
        if self.nativeEID != None:
            [self.state, self.error_code] = await self.native.read_value(fp_str, dp_str)

        if self.isLogging:
            self.log_value_state('read_channel')

        print(f"Relais actuator read channel: {self.name} state {self.state} "
              f"error code {self.error_code}")

        return self.state, self.error_code

    async def get_channel(self, channel: int):
        return self.state, self.error_code

    async def read(self):
        for i in range(self.nChannels):
            await self.read_channel(i)

    def write_channel(self, channel: int, state: str):
        self.state = state
        self.error_code = 0

        # TODO: specify fp and dp names
        fp_str = "SWITCH"
        dp_str = f"CHANNEL{channel}"

        if self.smartGridreadyEID != None:
            [self.error_code] = self.smartgridready.write_value(fp_str, dp_str, state)
        if self.nativeEID != None:
            [self.error_code] = self.native.write_value(fp_str, dp_str, state)

        if self.isLogging:
            self.log_value_state('write_channel')

        print(f"Relais actuator write channel: {self.name} state {self.state} "
              f"error code {self.error_code}")

        return self.error_code

  

class HeatPump(Device):
    # class for heat pump devices

    def __init__(self, *, name: str = "",
                 type: str = "",
                 smartGridreadyEID: str = "",
                 EID_param: str = "",
                 nativeEID: str = "",
                 simulationModel: str = "",
                 isLogging: bool = True,
                 communicationChannel: str = "",
                 param: dict = None
                 ):

        # initialize base class
        super().__init__(name=name, type=type, smartGridreadyEID=smartGridreadyEID, EID_param=EID_param, nativeEID=nativeEID,
                         simulationModel=simulationModel, isLogging=isLogging,
                         communicationChannel=communicationChannel, param = param)

       
        if param is None:
            param = {}


    async def read_device(self, functional_profile):
        self.value = 0
        self.error_code = 0
        fp_str = ""
        dp_str = ""

        # TODO: specify fp and dp names
        if functional_profile == "DHW":
            fp_str = "FP_DomHotwater"
            dp_str = f"OutsideAirTemp"
        if functional_profile == "BUFFER":
            fp_str = "FP_BufferStorage"
            dp_str = f"OutsideAirTemp"
        if functional_profile == "POWER":
            fp_str = "FP_PowerCtrl"
            dp_str = f"DP_ActualSpeed"

        if self.smartGridreadyEID != "None":
            [self.value, self.error_code] = await self.smartgridready_Comp.read_value(fp_str, dp_str)

        if self.nativeEID != "None":

            [self.value, self.unit, self.error_code] = await self.native.read_value(dp_str)

        if self.simulationModel != "None":
            [self.value, self.error_code] = await self.simulation.run_simulation_step(self.state)

        if self.isLogging:
            self.log_value_state('read_device')
    
        return self.value, self.error_code


    def write_device_setpoint(self, functional_profile, setpoint: float):
        self.value = setpoint
        self.error_code = 0
        fp_str = ""
        dp_str = ""

        # TODO: specify fp and dp names
        if functional_profile == "DHW":
            fp_str = "FP_DomHotwater"
            dp_str = f"DP_SetpointComfort"
        if functional_profile == "BUFFER":
            fp_str = "FP_BufferStorage"
            dp_str = f"DP_SetpointComfort"
        if functional_profile == "POWER":
            fp_str = "FP_PowerCtrl"
            dp_str = f"DP_SetpointSpeed"

        if self.smartGridreadyEID != None:
            [self.error_code] = self.smartgridready_Comp.write_value(fp_str, dp_str, setpoint)
        if self.nativeEID != None:
            [self.error_code] = self.native.write_value(fp_str, dp_str, setpoint)

        if self.isLogging:
            self.log_value_state('write_device_setpoint')

        print(f"Heat pump write device setpoint: {self.name} functional_profile {functional_profile} "
              f"fp_str {fp_str} dp_str {dp_str} state {self.state} value {self.value:.2f} "
              f"error code {self.error_code}")

        return self.error_code

    def switch_device(self, functional_profile: str, state: str):
        self.state = state
        self.error_code = 0
        fp_str = ""
        dp_str = ""

        # TODO: specify fp and dp names
        if functional_profile == "BASE":
            fp_str = "FP_Base"
            dp_str = f"DP_OpMode"
        if functional_profile == "DHW":
            fp_str = "FP_DomHotwater"
            dp_str = f"DP_OpMode"
        if functional_profile == "HEATCYCLE":
            fp_str = "FP_HeatCycle"
            dp_str = f"DP_OpMode"

        if self.smartGridreadyEID != None:
            [self.error_code] = self.smartgridready.write_value(fp_str, dp_str, state)
        if self.nativeEID != None:
            [self.error_code] = self.native.write_value(fp_str, dp_str, state)

        if self.isLogging:
            self.log_value_state('switch_device')

        print(f"Heat pump switch device: {self.name} functional_profile {functional_profile} "
              f"fp_str {fp_str} dp_str {dp_str} state {self.state} value {self.value:.2f} "
              f"error code {self.error_code}")

        return self.error_code

    async def read(self):
        await self.read_device("DHW")
class EVCharger(Device):
    # class for heat pump devices

    def __init__(self, *, name: str = "",
                 type: str = "",
                 smartGridreadyEID: str = "",
                 EID_param: str = "",
                 nativeEID: str = "",
                 simulationModel: str = "",
                 isLogging: bool = True,
                 communicationChannel: str = "",
                 address: str = "",
                 port: str = "",
                 minPower: float,
                 maxPower: float,
                 phases: str = ""):

        # initialize base class
        super().__init__(name=name, type=type, smartGridreadyEID=smartGridreadyEID,EID_param=EID_param, nativeEID=nativeEID,
                         simulationModel=simulationModel, isLogging=isLogging,
                         communicationChannel=communicationChannel)

        self.address = address
        self.port = port
        self.minPower = minPower
        self.maxPower = maxPower
        self.nominalPower = minPower
        self.phases = phases
        self.state = "OFF"



    async def read_power(self):
        self.value = 0
        self.error_code = 0

        # TODO: specify fp and dp names
        fp_str = "Power"
        dp_str = "ChargingCurrentAC"

        if self.smartGridreadyEID != None:
            [self.value, self.error_code] = await self.smartgridready_Comp.read_value(fp_str, dp_str)
        if self.nativeEID != None:
            [self.value, self.error_code] = await self.native.read_value(fp_str, dp_str)
        if self.simulationModel != None:
            [self.value, self.error_code] = await self.simulation.run_simulation_step(self.state)

        if self.phases == "ONE_PHASE":
            self.value = 230*self.value       # P = U*I
        elif self.phases == "THREE_PHASES":
            self.value = 3*230*self.value     # P = 3*U*I

        if self.isLogging:
            self.log_value_state('read_power')

        print(f"EV Charger read power: {self.name} "
              f"fp_str {fp_str} dp_str {dp_str} state {self.state} value {self.value:.2f} "
              f"error code {self.error_code}")

        return self.value, self.error_code

    def write_device_setpoint(self, functional_profile: str, setpoint: float):
        self.error_code = 0
        self.value = setpoint

        # TODO: specify fp and dp names
        fp_str = "PowerCtrl"
        dp_str = "SetChargingCurrentAC"

        if self.phases == "ONE_PHASE":
            self.value = setpoint / 230   # I = P/U
        elif self.phases == "THREE_PHASES":
            self.value = setpoint / (3*230)  # I = P/(3*U)

        if self.smartGridreadyEID != None:
            [self.error_code] = self.smartgridready_Comp.write_value(fp_str, dp_str, self.value)
        if self.nativeEID != None:
            [self.error_code] = self.native.write_value(fp_str, dp_str, self.value)

        if self.isLogging:
            self.log_value_state('write_device_setpoint')

        print(f"EV Charger write device setpoint: {self.name} "
              f"fp_str {fp_str} dp_str {dp_str} state {self.state} value {self.value:.2f} "
              f"error code {self.error_code}")

        return self.error_code

    def switch_device(self, functional_profile: str, state: str):
        self.error_code = 0
        self.state = state

        # TODO: specify fp and dp names
        fp_str = "PowerCtrl"
        dp_str = "SetMode"

        if self.smartGridreadyEID != None:
            [self.error_code] = self.smartgridready_Comp.write_value(fp_str, dp_str, state)
        if self.nativeEID != None:
            [self.error_code] = self.native.write_value(fp_str, dp_str, state)

        if self.isLogging:
            self.log_value_state('switch_device')

        print(f"EV Charger switch device: {self.name} "
              f"fp_str {fp_str} dp_str {dp_str} state {self.state} value {self.value:.2f} "
              f"error code {self.error_code}")


        return self.error_code


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
