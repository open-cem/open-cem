"""
-------------------------------------------------------
cem_lib_controllers
Library for OpenCEM
Contains classes for controllers
-------------------------------------------------------
Fachhochschule Nordwestschweiz, Institut für Automation
Authors: Prof. Dr. D. Zogg, S. Ferreira, Ch. Zeltner
Version: 2.0, October 2024
-------------------------------------------------------
"""


import logging
from OpenCEM.cem_lib_components import Device, PowerSensor, TemperatureSensor, RelaisActuator, HeatPump, EVCharger

class Controller:
    # base class for controller

    def __init__(self,name: str = ""):
        self.name = name
        self.type = None  # type of controller
        self.mainMeter = None  # main meter object
        self.deviceMeter = None  # device meter object
        self.controlledDevice = None # controlled device object
        self.controllerSettings = None # controller settings
        self.mode = 0  # controller mode (0 = off, 1 = on, 2 = high, etc.)

    def get_type(self):
        return self.type

    async def calc_controller(self, remainingPower: float):
        return 0, remainingPower

class SwitchingExcessController(Controller):
    # class for pv excess controller
    # switch device on when pv excess > power limit

    def __init__(self, *, name : str = "", mainMeter: PowerSensor, deviceMeter: PowerSensor, controlledDevice: Device,
                 controllerSettings):
        super().__init__(name)
        self.type = "SWITCHING_EXCESS_CONTROLLER"  # type of controller
        self.mainMeter = mainMeter  # main meter object
        self.deviceMeter = deviceMeter  # device meter object
        self.controlledDevice = controlledDevice # controlled device object
        self.powerLimit = controllerSettings["powerLimit"] # controller settings: power limit in kW
        self.powerHysteresis = controllerSettings["powerHysteresis"] # controller settings: power hysteresis in kW
        self.mode = 0  # controller mode (0 = off, 1 = on, 2 = high, etc.)
        self.excess = 0 # actual pv excess in kW

        print(f"Controller created: {self.name} type {self.type} "
              f"settings {controllerSettings}")


    def set_controllerSettings(self, controllerSettings):
        self.powerLimit = controllerSettings["powerLimit"]  # controller settings: power limit in kW
        self.powerHysteresis = controllerSettings["powerHysteresis"] # controller settings: power hysteresis in kW

    async def calc_controller(self, remainingPower: float):
        # output mode: on(1) or off(0)
        # output output: continuous controller output = excess (kW) 
        error_code = 0

        # calculate pv excess
        if remainingPower == None: # first call
            mainPower, unit, error_code  = await self.mainMeter.get_power() # get main power
            remainingPower = -mainPower # positive: import from grid, negative: export to grid

        if remainingPower > 0:   # remaining power available
            self.excess = remainingPower    # excess equal to remaining power

            # get own consumption of device
            if self.deviceMeter != None:    # device meter available
                ownConsumption, unit, error_code = await self.deviceMeter.get_power()
            else:
                if self.mode > 0:           # device running
                    ownConsumption = self.controlledDevice.nominalPower
                else:
                    ownConsumption = 0      # device not running

            #self.excess = self.excess + ownConsumption    # add own consumption in order to eliminate continuous cycling
            remainingPower = remainingPower - ownConsumption    # subtract own consumption from remaining power
        else:
            self.excess = 0
            remainingPower = 0
            ownConsumption = 0

        print(f"Controller calculated: {self.name} type {self.type} "
              f"excess {self.excess:.2f} ownConsumption {ownConsumption:.2f} "
              f"remainingPower {remainingPower:.2f}")

        old_mode = self.mode

        if self.excess > self.powerLimit:
            self.mode = 1
            if old_mode == 0:
                error_code = self.controlledDevice.switch_device(functional_profile=None,
                                                                 state="ON")  # switch device on
        if self.excess < self.powerLimit - self.powerHysteresis:
            self.mode = 0
            if old_mode == 1:
                error_code = self.controlledDevice.switch_device(functional_profile=None,
                                                                 state="OFF")  # switch device off

        return error_code, remainingPower

class DynamicExcessController(SwitchingExcessController):
    # class for pv excess controller
    # switch device on when excess > power limit
    # set device to actual power = pv access

    def __init__(self, *, name : str = "", mainMeter: PowerSensor, deviceMeter: PowerSensor, controlledDevice: Device,
                 controllerSettings):
        super().__init__(name=name, mainMeter=mainMeter, deviceMeter=deviceMeter, controlledDevice=controlledDevice,
                         controllerSettings=controllerSettings)
        self.type = "DYANMIC_EXCESS_CONTROLLER"  # type of controller
        self.power = 0

        print(f"Controller created: {self.name} type {self.type} "
              f"settings {controllerSettings}")


    async def calc_controller(self, remainingPower: float):
        # output mode: on(1) or off(0)
        # output output: continuous controller output = excess (kW)

        error_code, remainingPower = await super().calc_controller(remainingPower)      # calculate pv excess and switch device (inherited)
        error_code = 0

        if self.excess > self.powerLimit:   # write pv excess as power setpoint to device
           error_code = self.controlledDevice.write_device_setpoint(functional_profile="", setpoint=self.excess)

        return error_code, remainingPower

class TemperatureExcessController(SwitchingExcessController):
    # class for temperature excess controller (used for heat pumps)
    # variable rise of temperature setpoint when pv excess > power limit

    def __init__(self, *, name : str = "", mainMeter: PowerSensor, deviceMeter: PowerSensor, controlledDevice: HeatPump,
                 functionalProfile: str = "", controllerSettings):
        super().__init__(name=name, mainMeter=mainMeter, deviceMeter=deviceMeter, controlledDevice=controlledDevice,
                         controllerSettings=controllerSettings)
        self.type = "TEMPERATURE_EXCESS_CONTROLLER"  # type of controller
        self.functionalProfile = functionalProfile # functional profile (specifies function)
        # controller settings:
        self.tempEco = controllerSettings["tempEco"] # eco temperature (lowered)
        self.tempComfort = controllerSettings["tempComfort"] # comfort temperature (normal)
        self.tempMax = controllerSettings["tempMax"] # maximum temperature (pv excess)
        self.excessComfort = controllerSettings["excessComfort"] # power limit in kW to switch on tempComfort
        self.excessMax = controllerSettings["excessMax"] # power limit in kW for tempMax

        self.excess = 0 # actual pv excess in kW
        self.tempSetpoint = self.tempEco    # starting value for temperature setpoint
        self.mode = 0   # OFF at initialisation

        print(f"Controller created: {self.name} type {self.type} "
              f"settings {controllerSettings}")

    def set_controllerSettings(self, controllerSettings):
        self.tempEco = controllerSettings["tempEco"] # eco temperature (lowered)
        self.tempComfort = controllerSettings["tempComfort"] # comfort temperature (normal)
        self.tempMax = controllerSettings["tempMax"] # maximum temperature (pv excess)
        self.excessComfort = controllerSettings["excessComfort"] # power limit in kW to switch on tempComfort
        self.excessMax = controllerSettings["excessMax"] # power limit in kW for tempMax

    async def calc_controller(self, remainingPower: float):
        # output mode: on(1) or off(0)
        # output output: continuous controller output = excess (kW)

        error_code, remainingPower = await super().calc_controller(remainingPower)      # calculate pv excess and switch device (inherited)

        # calculate temperature setpoint from excess
        if self.excess > self.excessComfort:
            self.tempSetpoint = (self.excess-self.excessComfort)*(self.tempMax-self.tempComfort)/(self.excessMax-self.excessComfort)+self.tempComfort
            if self.tempSetpoint > self.tempMax:
                self.tempSetpoint = self.tempMax
            if self.tempSetpoint < self.tempComfort:
                self.tempSetpoint = self.tempComfort

        else:
            self.tempSetpoint = self.tempEco

        print(f"Temperature Controller calculated: {self.name} type {self.type} "
              f"excess {self.excess:.2f} tempSetpoint {self.tempSetpoint:.2f}")

        error_code = self.controlledDevice.write_device_setpoint(functional_profile=self.functionalProfile, setpoint=self.tempSetpoint)

        return error_code, remainingPower
