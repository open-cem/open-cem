# Generative AI was used for some Code

import asyncio
import logging
import math

import aiohttp
import time
from audioop import mul
from operator import truediv
from pprint import pprint
from pymodbus.constants import Endian
from sgr_library import SGrDevice

import random
import sys, os
from datetime import datetime, timedelta

# Smartgrid Ready Libraries


# pymodbus
from pymodbus.client import ModbusSerialClient, AsyncModbusTcpClient, AsyncModbusSerialClient

from sgr_library.modbusRTU_interface_async import SgrModbusRtuInterface
from sgr_library.payload_decoder import PayloadDecoder
from datetime import datetime

# Authentication Key and corresponding server for the Shelly Cloud
shelly_auth_key = "MTUyNjU5dWlk6D393AB193944CE2B1D84E0B573EAB1271DA6F2AF2BC54F67779F5BC27C31E90AD7C7075E0F813D8"
shelly_server_address = "https://shelly-54-eu.shelly.cloud/"

# Simulation parameters:
simulation_speed_up_factor = 1  # will be overwritten by setting yaml
sim_start_time = None



class OpenCEM_RTU_client: # TODO: remove or integrate in native implementation
    """
    creates a global RTU Client for OpenCEM. There can only be one client globally.
    If there already exist a smartGridready, put it as keyword argument global_client = client.
    """
    OpenCEM_global_RTU_client = None

    def __init__(self, port: str = "COM5", baudrate: int = 19200, parity: str = "E", client_timeout: int = 1, *,
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


class SmartGridreadyComponent:
    # class for component with smartgridready compatibility

    def __init__(self, XML_file: str):

        interface_file = XML_file
        self.sgr_component   = SGrDevice()
        self.sgr_component.update_xml_spec(interface_file)
        self.sgr_component.build()
        self.sgr_component.connect()

        print(f"SmartGridready Component created: {XML_file}")


    async def read_value(self, functional_profile: str, data_point: str):
        # read one value from a given data point within a functional profile
        error_code = 0
        dp = self.sgr_component.get_data_point((functional_profile, data_point))
        value = await dp.read()

        print(f"SmartGridready Component read value: {functional_profile, data_point, value}")

        return [value, dp.unit(), error_code]

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

        self.sgr_component.setval(functional_profile, data_point, value)

        print(f"SmartGridready Component write value: {functional_profile, data_point, value}")

        return error_code

    def read_device_profile(self):
        # get basic info from device profile such as name, nominal power consumption, level of operation, etc.

        device_profile = self.sgr_component.get_device_profile()
        return [device_profile.brand_name, device_profile.nominal_power, device_profile.dev_levelof_operation]

    def read_device_information(self):
        name = self.sgr_component.get_device_name()
        manufacturer = self.sgr_component.get_manufacturer()
        bus_type = self.sgr_component.get_modbusInterfaceSelection()

        return name, manufacturer, bus_type

class NativeComponent:
    # class for component with native implementation

    def __init__(self, YAML_file: str):

        self.interface_file = YAML_file

        # TODO: add code here - read YAML file and store functional profiles / data points
        #                       connect to device

        print(f"Native Component created: {YAML_file}")


    async def read_value(self, functional_profile: str, data_point: str):
        # read one value from a given data point within a functional profile
        error_code = 0

        # TODO: add code here - read value from data_point
        value = 0
        unit = None

        print(f"Native Component value read: {value}")

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

        # TODO: add code here - write value to data point
        value = 0
        unit = None

        print(f"Native Component value write: {value} unit {unit}")

        return error_code

class SimulatedComponent:
    # class for simulated component (not existing in hardware)

    def __init__(self, model: str):
        self.model = model
        self.max_power = 0
        self.min_power = 0
        self.nominal_power = 0
        self.min_temperature = 0
        self.max_temperature = 0

        # TODO: read parameter file with model simulation settings instead of hard coding
        if self.model == "PV PLANT":
            self.max_power = 10
        if self.model == "MAIN POWER":
            self.max_power = 10
        if self.model == "HEAT PUMP":
            self.nominal_power = 3
        if self.model == "ROOM TEMPERATURE":
            self.min_temperature = 18
            self.max_temperature = 22
        self.value = 0
        self.unit = ''

        print(f"Simulated Component created: {self.model}")


    async def run_simulation_step(self, state: str = "", setpoint: float = 0):
        self.value = 0
        self.unit = 'KILOWATTS'

        if sim_start_time is None:  # check if there already exists a start_time
            t_loop_start = round(asyncio.get_running_loop().time(), 2)
        else:
            t_loop_start = sim_start_time

        t = round(asyncio.get_running_loop().time() - t_loop_start, 2)

        print(f"Simulated Component {self.model} run simulation step at time {t}")

        if self.model == "PV_PLANT":
            t_shifted = t - (6 * 60 * 60 / simulation_speed_up_factor)  # Subtracting 6 hours in seconds

            # power_max is amplitude of the sine function
            self.value = round(
                self.max_power * math.sin(simulation_speed_up_factor * 2 * math.pi * (t_shifted / 86400)), 2)
            if self.value <= 0:
                self.value = 0

        if self.model == "MAIN_POWER":
            t_shifted = t - (6 * 60 * 60 / simulation_speed_up_factor)  # Subtracting 6 hours in seconds

            # power_max is amplitude of the sine function
            production = round(
                self.max_power * math.sin(simulation_speed_up_factor * 2 * math.pi * (t_shifted / 86400)), 2)
            consumption = random.uniform(0, self.max_power)
            self.value = production - consumption

        if self.model == "HEAT_PUMP":
            if state == "ON":
                self.value = self.nominal_power
            else:
                self.value = 0

        if self.model == "ELECTRIC_HEATER":
            if state == "ON":
                self.value = self.nominal_power
            else:
                self.value = 0

        if self.model == "EV_CHARGER":
            if state == "ON":
                self.value = setpoint
            else:
                self.value = 0

        if self.model == "ROOM_TEMPERATURE":
            t_shifted = t - (2 * 60 * 60 / simulation_speed_up_factor)  # Subtracting 3 hours in seconds

            # temperature is amplitude of the sine function
            amplitude = self.max_temperature - self.min_temperature
            self.value = self.min_temperature + round(
                amplitude * math.sin(simulation_speed_up_factor * 2 * math.pi * (t_shifted / 86400)), 2)
            self.unit = 'CELSIUS'

        print(f"Simulated value {self.value} unit {self.unit}")

        error_code = 0
        return [self.value, self.unit, error_code]

class Device():
    # base class for any device including sensors and actuators

    def __init__(self, *, name: str = "", type: str = "", smartGridreadyEID: str = "", nativeEID: str = "",
                 simulationModel: str = "", isLogging: bool = True,
                 communicationChannel: str = ""):

        self.name = name
        self.type = type
        self.smartGridreadyEID = smartGridreadyEID
        self.nativeEID = nativeEID
        self.simulationModel = simulationModel
        self.isLogging = isLogging
        self.communicationChannel = communicationChannel
        self.nominalPower = 0
        self.state = 0
        self.value = 0

        if smartGridreadyEID != None:
            self.smartgridready = SmartGridreadyComponent(smartGridreadyEID)

        if nativeEID != None:
            self.native = NativeComponent(nativeEID)

        if simulationModel != None:
            self.simulation = SimulatedComponent(simulationModel)

        print(f"Device created: {self.name} type {self.type}")

    # abstract methodes

    def read(self):
        pass

    def switch_device(self, functional_profile: str, state: str):
        return 0        # error code

    def write_device_setpoint(self, functional_profile: str, setpoint: float):
        return 0        # error code

    def log_value_state(self):
        # logs the value of a device. Log depends on what device it is
        logger = logging.getLogger("device_logger")
        logger.info(
            f"{self.name};{self.type};{self.value};{self.state}")
        

class PowerSensor(Device):
    # derived class for power sensor
    sleep_between_requests = 0.05  # TODO: Time the program will wait after a RTU request in seconds -> move to extra properties

    def __init__(self, *, name: str = "", type: str = "",
                 smartGridreadyEID: str = "",
                 nativeEID: str = "",
                 simulationModel: str = "",
                 isLogging: bool = True,
                 communicationChannel: str = "",
                 address: str ="",
                 has_energy_import: bool = False,
                 has_energy_export: bool = False,
                 maxPower: float):

        # initialize sensor
        super().__init__(name=name, type=type, smartGridreadyEID=smartGridreadyEID, nativeEID=nativeEID,
                         simulationModel=simulationModel, isLogging=isLogging, communicationChannel=communicationChannel)

        self.address = address
        self.has_energy_import = has_energy_import
        self.has_energy_export = has_energy_export
        self.maxPower = maxPower
        self.energy_value_import = 0
        self.energy_value_export = 0

    async def read_power(self):
        """
        returns the total power of a powersensor in kW. For not SmartGridReady devices you need to add_RTU_Power_entry() first.
        :returns: the power value, the unit, and error code
        """
        value = 0
        unit = 0
        error_code = 0

        if self.smartGridreadyEID != None:
            [value, unit, error_code] = await self.smartgridready.read_value_with_conversion('ActivePowerAC',
                                                                                     'ActivePowerACtot')
        if self.nativeEID != None:
            [value, unit, error_code] = await self.native.read_value_with_conversion('ActivePowerAC',
                                                                                     'ActivePowerACtot')
        if self.simulationModel != None:
            [value, unit, error_code] = await self.simulation.run_simulation_step()

        await asyncio.sleep(PowerSensor.sleep_between_requests)

        if error_code == 0:
            if value <= self.maxPower:
                self.value = value
        elif self.isLogging:
            self.log_value_state()

        print(f"Power sensor read power: {self.name} value {self.value} unit {unit} error code {error_code}")

        return self.value, unit, error_code

    async def read_energy_import(self):
        """
        returns the energy import of a powersensor in kW. For not SmartGridReady devices you need to add_RTU_EnergyImport_entry() first.
        :returns: the energy import value, the unit, and error code. Has_energy_import has to be set to True in the power_sensor init
        """
        value = 0
        unit = 0
        error_code = 0

        if self.smartGridreadyEID != None and self.has_energy_import:
            [value, unit, error_code] = await self.smartgridready.read_value_with_conversion('ActiveEnerBalanceAC',
                                                                                             'ActiveImportAC')
        if self.nativeEID != None and self.has_energy_import:
            [value, unit, error_code] = await self.native.read_value_with_conversion('ActiveEnerBalanceAC',
                                                                                         'ActiveImportAC')
        await asyncio.sleep(PowerSensor.sleep_between_requests)

        if error_code == 0:
            self.energy_value_import = value
        elif self.isLogging:
            self.log_value_state()

        print(f"Power sensor read energy import: {self.name} value {self.energy_value_import} unit {unit} "
              f"error code {error_code}")

        return self.energy_value_import, unit, error_code

    async def read_energy_export(self):
        """
        returns the energy export of a powersensor in kW. For not SmartGridReady devices you need to add_RTU_EnergyExport_entry() first.
        :returns: the energy export value, the unit, and error code. Has_energy_export has to be set to True in the power_sensor init
        """
        value = 0
        unit = 0
        error_code = 0

        if self.smartGridreadyEID != None and self.has_energy_export:
            [value, unit, error_code] = await self.smartgridready.read_value_with_conversion('ActiveEnerBalanceAC',
                                                                                             'ActiveExportAC')
        if self.nativeEID != None and self.has_energy_export:
            [value, unit, error_code] = await self.native.read_value_with_conversion('ActiveEnerBalanceAC',
                                                                                                 'ActiveExportAC')
        await asyncio.sleep(PowerSensor.sleep_between_requests)

        if error_code == 0:
            self.energy_value_export = value
        elif self.isLogging:
            self.log_value_state()

        print(f"Power sensor read energy export: {self.name} value {self.energy_value_export} unit {unit} "
              f"error code {error_code}")

        return self.energy_value_export, unit, error_code

    async def read_all(self):
        power_value = await self.read_power()
        energy_value_import = await self.read_energy_import()
        energy_value_export = await self.read_energy_export()
        return power_value, energy_value_import, energy_value_export

    def log_value_state(self):

        if "OpenCEM_statistics" in logging.Logger.manager.loggerDict.keys():
            logger = logging.getLogger("OpenCEM_statistics")
            logger.info(
                f"{self.name};{str(self.address)};{self.value};KILOWATT")
            if self.has_energy_import:
                logger.info(
                    f"{self.name};{str(self.address)};{self.energy_value_import};KILOWATT_HOURS")
            if self.has_energy_export:
                logger.info(
                    f"{self.name};{str(self.address)};{self.energy_value_export};KILOWATT_HOURS")


class TemperatureSensor(Device):
    # derived class for temperature sensor

    def __init__(self, *, name: str = "", type: str = "",
                 smartGridreadyEID: str = "",
                 nativeEID: str = "",
                 simulationModel: str = "",
                 isLogging: bool = True,
                 communicationChannel: str = "",
                 address: str = "",
                 maxTemp: int, minTemp: int):

        # initialize sensor
        super().__init__(name=name, type=type, smartGridreadyEID=smartGridreadyEID, nativeEID=nativeEID,
                         simulationModel=simulationModel, isLogging=isLogging, communicationChannel=communicationChannel)
        self.address = address
        self.maxTemp = maxTemp
        self.minTemp = minTemp
        self.value = 0

    async def read_temperature(self):
        value = 0
        unit = 0
        error_code = 0

        if self.smartGridreadyEID != None:  # TODO: specify fp and dp names
            [value, unit, error_code] = await self.smartgridready.read_value_with_conversion('Temperature',
                                                                                             'Degree')
        if self.nativeEID != None: # TODO: specify fp and dp names
            [value, unit, error_code] = await self.native.read_value_with_conversion('Temperature',
                                                                                     'Degree')
        if self.simulationModel != None:
            [value, unit, error_code] = await self.simulation.run_simulation_step()

        await asyncio.sleep(PowerSensor.sleep_between_requests)

        if error_code == 0:
            if (value >= self.minTemp) and (value <= self.maxTemp):
                self.value = value
        elif self.isLogging:
            self.log_value_state()

        print(f"Temperature sensor read temperature: {self.name} value {self.value} unit {unit} "
              f"error code {error_code}")

        return self.value, unit, error_code

    def log_value_state(self):
        if "OpenCEM_statistics" in logging.Logger.manager.loggerDict.keys():
            logger = logging.getLogger("OpenCEM_statistics")
            logger.info(
                f"{self.name};TEMPERATURE;{self.value};CELSIUS")


class RelaisActuator(Device):
    # derived class for relais switch

    def __init__(self, *, name: str = "", type: str = "",
                 smartGridreadyEID: str = "",
                 nativeEID: str = "",
                 simulationModel: str = "",
                 isLogging: bool = True,
                 communicationChannel: str = "",
                 address: str = "",
                 nChannels: int = 1):

        # initialize actuator
        super().__init__(name=name, type=type, smartGridreadyEID=smartGridreadyEID, nativeEID=nativeEID,
                         simulationModel=simulationModel, isLogging=isLogging, communicationChannel=communicationChannel)
        self.address = address
        self.nChannels = nChannels

        #self.values = [0] * self.nChannels # initialize values to 0 for each channel

    async def read_channel(self, channel: int):
        state = 0
        error_code = 0

        # TODO: specify fp and dp names
        fp_str = "SWITCH"
        dp_str = f"CHANNEL{channel}"

        if self.smartGridreadyEID != None:
            [state, error_code] = await self.smartgridready.read_value(fp_str, dp_str)
        if self.nativeEID != None:
            [state, error_code] = await self.native.read_value(fp_str, dp_str)

        if error_code == 0:
            self.state = state
        elif self.isLogging:
            self.log_value_state()

        print(f"Relais actuator read channel: {self.name} state {self.state} "
              f"error code {error_code}")

        return self.value, error_code

    def write_channel(self, channel: int, state: str):
        error_code = 0

        # TODO: specify fp and dp names
        fp_str = "SWITCH"
        dp_str = f"CHANNEL{channel}"

        if self.smartGridreadyEID != None:
            [error_code] = self.smartgridready.write_value(fp_str, dp_str, state)
        if self.nativeEID != None:
            [error_code] = self.native.write_value(fp_str, dp_str, state)

        if error_code == 0:
            self.state = state
        elif self.isLogging:
            self.log_value_state()

        print(f"Relais actuator write channel: {self.name} state {self.state} "
              f"error code {error_code}")

        return error_code

    def log_value_state(self):
        if "OpenCEM_statistics" in logging.Logger.manager.loggerDict.keys():
            logger = logging.getLogger("OpenCEM_statistics")
            logger.info(
                f"{self.name};RELAIS;{self.state};STATE")



class HeatPump(Device):
    # class for heat pump devices

    def __init__(self, *, name: str = "", type: str = "", smartGridreadyEID: str = "", nativeEID: str = "",
                 simulationModel: str = "", isLogging: bool = True,
                 communicationChannel: str = "", address: str = "", port: str = "",
                 minPower: float, maxPower: float):

        # initialize base class
        super().__init__(name=name, type=type, smartGridreadyEID=smartGridreadyEID, nativeEID=nativeEID,
                         simulationModel=simulationModel, isLogging=isLogging,
                         communicationChannel=communicationChannel)

        self.address = address
        self.port = port
        self.minPower = minPower
        self.maxPower = maxPower
        self.state = "OFF"

    async def read_device(self, functional_profile):
        value = 0
        error_code = 0
        fp_str = ""
        dp_str = ""

        # TODO: specify fp and dp names
        if functional_profile == "DHW":
            fp_str = "FP_DomHotwater"
            dp_str = f"DP_ActualTemperature"
        if functional_profile == "BUFFER":
            fp_str = "FP_BufferStorage"
            dp_str = f"DP_ActualTemperature"
        if functional_profile == "POWER":
            fp_str = "FP_PowerCtrl"
            dp_str = f"DP_ActualSpeed"

        if self.smartGridreadyEID != None:
            [value, error_code] = await self.smartgridready.read_value(fp_str, dp_str)
        if self.nativeEID != None:
            [value, error_code] = await self.native.read_value(fp_str, dp_str)
        if self.simulationModel != None:
            [value, error_code] = await self.simulation.run_simulation_step(self.state)

        if error_code == 0:
            self.value = value
        elif self.isLogging:
            self.log_value_state()

        print(f"Heat pump read device: {self.name} functional_profile {functional_profile}"
              f"fp_str {fp_str} dp_str {dp_str} state {self.state} value {self.value} "
              f"error code {error_code}")

        return self.value, error_code

    def write_device_setpoint(self, functional_profile, setpoint: float):
        error_code = 0
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
            [error_code] = self.smartgridready.write_value(fp_str, dp_str, setpoint)
        if self.nativeEID != None:
            [error_code] = self.native.write_value(fp_str, dp_str, setpoint)

        if error_code == 0:
            self.value = setpoint
        elif self.isLogging:
            self.log_value_state()

        print(f"Heat pump write device setpoint: {self.name} functional_profile {functional_profile}"
              f"fp_str {fp_str} dp_str {dp_str} state {self.state} value {self.value} "
              f"error code {error_code}")

        return error_code

    def switch_device(self, functional_profile: str, state: str):
        error_code = 0
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
            [error_code] = self.smartgridready.write_value(fp_str, dp_str, state)
        if self.nativeEID != None:
            [error_code] = self.native.write_value(fp_str, dp_str, state)

        if error_code == 0:
            self.state = state
        elif self.isLogging:
            self.log_value_state()

        print(f"Heat pump switch device: {self.name} functional_profile {functional_profile}"
              f"fp_str {fp_str} dp_str {dp_str} state {self.state} value {self.value} "
              f"error code {error_code}")

        return error_code

class EVCharger(Device):
    # class for heat pump devices

    def __init__(self, *, name: str = "", type: str = "", smartGridreadyEID: str = "", nativeEID: str = "",
                 simulationModel: str = "", isLogging: bool = True,
                 communicationChannel: str = "", address: str = "", port: str = "",
                 minPower: float, maxPower: float, phases: str = ""):

        # initialize base class
        super().__init__(name=name, type=type, smartGridreadyEID=smartGridreadyEID, nativeEID=nativeEID,
                         simulationModel=simulationModel, isLogging=isLogging,
                         communicationChannel=communicationChannel)

        self.address = address
        self.port = port
        self.minPower = minPower
        self.maxPower = maxPower
        self.phases = phases
        self.state = "OFF"

    async def read_power(self):
        value = 0
        error_code = 0

        # TODO: specify fp and dp names
        fp_str = "Power"
        dp_str = "ChargingCurrentAC"

        if self.smartGridreadyEID != None:
            [value, error_code] = await self.smartgridready.read_value(fp_str, dp_str)
        if self.nativeEID != None:
            [value, error_code] = await self.native.read_value(fp_str, dp_str)
        if self.simulationModel != None:
            [value, error_code] = await self.simulation.run_simulation_step(self.state)

        if self.phases == "ONE_PHASE":
            value = 230*value       # P = U*I
        elif self.phases == "THREE_PHASES":
            value = 3*230*value     # P = 3*U*I

        if error_code == 0:
            self.value = value
        elif self.isLogging:
            self.log_value_state()

        print(f"EV Charger read power: {self.name} "
              f"fp_str {fp_str} dp_str {dp_str} state {self.state} value {self.value} "
              f"error code {error_code}")

        return self.value, error_code

    def write_device_setpoint(self, functional_profile: str, setpoint: float):
        error_code = 0
        value = 0

        # TODO: specify fp and dp names
        fp_str = "PowerCtrl"
        dp_str = "SetChargingCurrentAC"

        if self.phases == "ONE_PHASE":
            value = setpoint / 230   # I = P/U
        elif self.phases == "THREE_PHASES":
            value = setpoint / (3*230)  # I = P/(3*U)

        if self.smartGridreadyEID != None:
            [error_code] = self.smartgridready.write_value(fp_str, dp_str, value)
        if self.nativeEID != None:
            [error_code] = self.native.write_value(fp_str, dp_str, value)

        if error_code == 0:
            self.value = value
        elif self.isLogging:
            self.log_value_state()

        print(f"EV Charger write device setpoint: {self.name} "
              f"fp_str {fp_str} dp_str {dp_str} state {self.state} value {self.value} "
              f"error code {error_code}")

        return error_code

    def switch_device(self, functional_profile: str, state: str):
        error_code = 0

        # TODO: specify fp and dp names
        fp_str = "PowerCtrl"
        dp_str = "SetMode"

        if self.smartGridreadyEID != None:
            [error_code] = self.smartgridready.write_value(fp_str, dp_str, state)
        if self.nativeEID != None:
            [error_code] = self.native.write_value(fp_str, dp_str, state)

        if error_code == 0:
            self.state = state
        elif self.isLogging:
            self.log_value_state()

        print(f"EV Charger switch device: {self.name} "
              f"fp_str {fp_str} dp_str {dp_str} state {self.state} value {self.value} "
              f"error code {error_code}")


        return error_code


class CommunicationChannel: # TODO: adapt - still necessary?
    # base class to describe a communication channel
    def __init__(self, type, extra):
        self.type = type

        # decision tree for CommunicationChannel type
        match self.type:

            case "MODBUS_TCP": # TODO: check this
                #address = extra["address"]
                #port = extra["port"]
                #self.client = AsyncModbusTcpClient(host=address, port=port)
                pass

            case "MODBUS_RTU":
                port = extra["port"]
                baudrate = extra["baudrate"]
                match extra["parity"]:
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
                self.shelly_auth_key = extra["authKey"]
                self.shelly_server_address = extra["serverAddress"]
            case "SMARTME_CLOUD":
                self.client = None
                self.shelly_auth_key = extra["authKey"]
                self.shelly_server_address = extra["serverAddress"]

            # general http client for the OpenCEM (for communication with GUI, etc.)
            case "HTTP_MAIN":
                self.client = aiohttp.ClientSession()
            case _:
                raise NotImplementedError(f"Communication {type} not known.")
